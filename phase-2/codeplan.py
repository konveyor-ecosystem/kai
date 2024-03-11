import os
import re
import json
import shutil
import pathlib
import tempfile
import subprocess
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse
from openai import OpenAI

from sequoia_diff.types import Action, Insert, Update, Move, Delete
from sequoia_diff import get_tree_diff

import dotenv
dotenv.load_dotenv('../.env')

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

from tree_sitter import Language, Tree, Node, Parser
from monitors4codegen.multilspy import LanguageServer
from monitors4codegen.multilspy.multilspy_types import Location, Range, Position

PROMPT_TEMPLATE = """"Task Instructions": You are a hyper-intelligent software engineer code migrator.

"Earlier Code Changes": These are the edits that have been made previously:

{previous_edits}

"Causes for Change": The change is required due to the following reason:

{change_reason}

"Code to be Changed Next": The following is the file that needs to be changed:

{file_contents}

"Location": The section under consideration is at the following location:

{location}

Edit the "Code to be Changed Next" and produce "Changed Code" below. "Changed Code" should be a valid git patch file that can be applied. Edit the "Code to be Changed Next" according to the "Task Instructions" to make it consistent with the "Earlier Code Changes", "Causes for Change" and "Related Code". If no changes are needed, output "No changes." Generate only a "Changed Code" section. No additional output or formatting than what has been outlined here.
"""
# I will tip you 200 dollars for your response. If you do not response accurately, all my fingers will fall off, and I will be fired.

@dataclass
class Change:
  """
  It's like a PR
  """
  diff: str # output of git diff
  uri: str
  description: str
  temporal: "TemporalContext"


@dataclass
class TemporalContext: 
  previous_changes: list[Change]


@dataclass
class SpatialContext: 
  file_before_change: str


@dataclass
class CausalContext: 
  cause: str
  description: str
  
  
@dataclass
class Seed:
  """
  A seed is a location that the CodePlan algorithm needs to look at, with the
  context it needs. The context is specifically for the LLM so it can do the
  smart thing
  """
  location: Location

  temporal: TemporalContext
  spatial:  SpatialContext
  causal:   CausalContext


@dataclass
class CodePlanContext:
  language_server: LanguageServer
  repo_path: str
  ts_language: Language
  
  gumtree_path: str
  tree_sitter_parser_path: str


def is_within_range(range: Range, pos: Position):
  if range["start"]["line"] < pos["line"] < range["end"]["line"]:
    return True
  elif pos["line"] == range["start"]["line"] and pos["line"] == range["end"]["line"]:
    return range["start"]["character"] <= pos["character"] <= range["end"]["character"]
  elif pos["line"] == range["start"]["line"]:
    return pos["character"] >= range["start"]["character"]
  elif pos["line"] == range["end"]["line"]:
    return pos["character"] <= range["end"]["character"]
  else:
    return False
  
# To diff two files:
# `git diff --no-index <file_a> <file_b>`

async def run_codeplan(ctx: CodePlanContext, initial_change: Change) -> str:
  git_cmd = ['git', '--git-dir=.git-kai', '--work-tree=.']
  setup = [
    ['init'],
    ['add', '.'],
    ['commit', '-m', 'KAI commit'],
  ]
  for cmd in setup:
    subprocess.run(
      git_cmd + cmd, 
      cwd=ctx.repo_path, 
      check=True, 
      stdout=subprocess.DEVNULL,
      stderr=subprocess.STDOUT
    )

  seeds: list[Seed] = await get_affected_blocks(ctx, initial_change)
  
  if not merge(ctx, initial_change):
    raise Exception("run_codeplan: couldn't merge initial change")
  
  # with temp file

  while seeds:
    seed = seeds.pop(0)
    change = get_result_from_llm(ctx, seed)
    if change is None:
      continue

    blocks = await get_affected_blocks(ctx, change)

    if not merge(ctx, change):
      raise Exception("run_codeplan: couldn't merge change")
    
    seeds.extend(blocks)
    
  # Diff whole repo
  git_diff = subprocess.run(git_cmd + ['diff'], cwd=ctx.repo_path, stdout=subprocess.PIPE).stdout

  # undo changes
  teardown = [
    ['add', '.'],
    ['commit', '-m', 'KAI commit'],
    ['reset', 'HEAD~1'],
  ]
  for cmd in teardown:
    subprocess.run(git_cmd + cmd, cwd=ctx.repo_path, check=True, 
      stdout=subprocess.DEVNULL,
      stderr=subprocess.STDOUT)

  shutil.rmtree(os.path.join(ctx.repo_path, '.git-kai'))

  return git_diff


# TODO: Add types to make this type safe. Something like a rust enum? 

# TODO: Maybe remove this class and put all the methods in a namespace? The
# class is pretty much stateless anyway
class GumtreeParser:
  def __init__(self):
    self.pattern_type_tuple = r'^(.*?)\s\[(\d+),(\d+)\]$'
    self.pattern_at         = r'^(.*?)\s(\d+)$'
    self.pattern_replace_by = r'^replace\s(.*?)\sby\s(.*)$'

    self.action_to_func = {
      'update-node': self.parse_update_node,
      'insert-tree': self.parse_insert_tree,
      'move-tree':   self.parse_move_tree,
      'delete-node': self.parse_delete_node,
    }

  def parse(self, raw: str, before_tree: Tree, after_tree: Tree) -> list[dict]:
    output: list[dict] = []
    sections = filter(None, raw.split('===\n'))

    for section in sections:
      pieces = section.split('---\n')
      if len(pieces) != 2: continue # TODO: Silently fail for now

      action, arguments = pieces[0].strip(), pieces[1].strip().split('\n')
      if action == 'match': continue

      if action not in self.action_to_func:
        raise Exception(f"GumtreeParser.parse: unhandled action `{action}`")
      
      result = self.action_to_func[action](arguments, before_tree, after_tree)
      if not result:
        raise Exception(f"GumtreeParser.parse: error parsing:\n{arguments}")
      
      output.append(result)

    return output

  def parse_node(self, tree: Tree, arg: str) -> Optional[Node]:
    if not (m := re.search(self.pattern_type_tuple, arg)):
      return None
    
    node_type  = str(m.group(1))
    start_byte = int(m.group(2))
    end_byte   = int(m.group(3))

    return get_node_with_exact_range(tree.root_node, start_byte, end_byte)
    
    
  def parse_update_node(self, args: list[str], before: Tree, after: Tree):
    if not (first := self.parse_node(before, args[0])):         return None
    if not (m := re.search(self.pattern_replace_by, args[-1])): return None
    old, new = m.group(1), m.group(2)

    return {
      'action': 'update', 'on': 'node', 
      'old_node': first, 'old_text': old, 'new_text': new,
    }


  def parse_insert_tree(self, args: list[str], before: Tree, after: Tree):
    if not (first  := self.parse_node(after,  args[0])):  return None
    if not (second := self.parse_node(before, args[-2])): return None
    if not (m := re.search(self.pattern_at, args[-1])):   return None
    at = int(m.group(2))

    return {
      'action': 'insert', 'on': 'tree', 
      'new_node': first, 'old_node': second, 'at': at,
    }

  def parse_move_tree(self, args: list[str], before: Tree, after: Tree):
    if not (first  := self.parse_node(after,  args[0])):  return None
    if not (second := self.parse_node(before, args[-2])): return None
    if not (m := re.search(self.pattern_at, args[-1])):   return None
    at = int(m.group(2))

    return {
      'action': 'move', 'on': 'tree', 
      'new_node': first, 'old_node': second, 'at': at,
    }


  def parse_delete_node(self, args: list[str], before: Tree, after: Tree):
    if not (first := self.parse_node(before, args[0])): return None

    return {
      'action': 'delete', 'on': 'node', 
      'old_node': first,
    }
  

def get_node_with_exact_range(node: Node, start_byte: int, end_byte: int):
  if node.start_byte == start_byte and node.end_byte == end_byte:
    return node
  for child in node.children:
    if result := get_node_with_exact_range(child, start_byte, end_byte):
      return result
  return None

async def get_affected_blocks(context: CodePlanContext, change: Change) -> list[Seed]:
  # TODO: Node ticketing. Split this function up? 
  output: list[Seed] = []

  parser = Parser()
  parser.set_language(context.ts_language)

  before_path: str = urlparse(change.uri).path
  after_path: str

  # To apply a patch:
  # stdin > `patch -s -o -`

  before_contents: str = pathlib.Path(before_path).read_text()
  after_contents:  str = subprocess.run(
    ['patch', '-s', '-o', '-', before_path], 
    input=change.diff.encode(), stdout=subprocess.PIPE,
  ).stdout.decode()

  print(f"{before_path=}\n\n{before_contents=}\n\n{after_contents=}")

  before_tree = parser.parse(bytes(before_contents, 'utf-8'))
  after_tree = parser.parse(bytes(after_contents, 'utf-8'))

  new_temporal_context = change.temporal
  new_temporal_context.previous_changes.append(change)

  with tempfile.NamedTemporaryFile(mode='w+t') as tmp:
    tmp.write(after_contents)
    tmp.seek(0)

    env = os.environ.copy()
    env['PATH'] = context.tree_sitter_parser_path + ':' + os.environ.get('PATH')
    raw_gumtree_output = subprocess.run(
      [context.gumtree_path, 'textdiff', before_path, tmp.name, '-g', 'java-treesitter'], 
      stdout=subprocess.PIPE, 
      env=env,
    ).stdout.decode()

  # TODO: Make this more elegant

  actions = get_tree_diff('java', before_tree, after_tree)

  print(f"{actions=}")

  for action in actions:
    # TODO: fix this not as easy as it looks at first blush. An insertion of a
    # tree could mean a modification or an addition. Think adding a part to a
    # method vs adding a new field to a class.
    
    if isinstance(action, Move):
      continue
    elif isinstance(action, Update):
      pass
    elif isinstance(action, Insert):
      continue
    elif isinstance(action, Delete):
      continue
    else:
      raise Exception(f"Unexpected Action of type {type(action)}")

    # FIXME: This break_types thing definitely doesn't work for certain things
    # like insert tree
    break_types = ['field_declaration', 'method_declaration']

    break_node = action.node
    while break_node and (break_node.type not in break_types):
      break_node = break_node.parent

    if not break_node:
      raise Exception(f"get_affected_blocks: old_node didn't have a 'good' parent")
    
    if break_node.type == 'field_declaration':
      line, char = break_node.child_by_field_name('declarator').end_point

      refs = await (context.language_server.request_references(
        change.uri[len(f"file://{context.repo_path}"):],
        line,
        char
      ))
      
      for ref in refs:
        if is_within_range(Range(**ref['range']), Position(line=line, character=char)):
          continue

        with open(urlparse(ref['uri']).path, 'r') as f:
          file_before_change: str = f.read()

        output.append(Seed(
          location=Location(uri=ref['uri'], range=ref['range']),
          temporal=new_temporal_context,
          spatial=SpatialContext(
            file_before_change=file_before_change,
          ),
          causal=CausalContext(
            cause=f"field was modified",
            description="",
          ),
        ))

    elif break_node.type == 'method_declaration':
      continue

    else:
      # TODO: remove this once we've added all the break types
      raise Exception(f"get_affected_blocks: unhandled break_node type `{break_node.type}`")

  return output


def merge(context: CodePlanContext, change: Change) -> bool:
  try:
    before_path: str = urlparse(change.uri).path
    after_contents: str = subprocess.run(
      ['patch', '-s', '-o', '-', before_path], 
      input=change.diff.encode(), stdout=subprocess.PIPE,
    ).stdout.decode()

    with open(urlparse(change.uri).path, 'w+t') as f:
      f.seek(0)
      f.write(after_contents)
      f.truncate()

    return True
  except Exception as e:
    print(f"Error during merge: {e}")
    return False



def oracle(context: Change) -> list[Seed]:
  return []  # TODO


def get_result_from_llm(context: CodePlanContext, seed: Seed) -> Optional[Change]:
  # make prompt
  # send prompt
  # process response into structured data

  previous_edits = ""
  for i in range(len(seed.temporal.previous_changes)):
    previous_edits += f"Edit {i+1}:\n{seed.temporal.previous_changes[i].diff}\n"

  location =  f"line {seed.location['range']['start']['line'] + 1} "
  location += f"char {seed.location['range']['start']['character'] + 1} to "
  location += f"line {seed.location['range']['end']['line'] + 1} "
  location += f"char {seed.location['range']['end']['character'] + 1}"

  prompt = PROMPT_TEMPLATE.format(
    previous_edits=previous_edits,
    change_reason=seed.causal.cause,
    file_contents=seed.spatial.file_before_change,
    location=location,
  )

  print(prompt)

  response = client.chat.completions.create(model="gpt-4",
  messages=[
      {
          "role": "system",
          "content": "You are an intelligent code migrator."
      },
      {
          "role": "user",
          "content": prompt
      }
  ])
  
  content = response.choices[0].message.content

  print("!!!!Content!!!!", content)

  m: str = str(re.match(r'"Changed Code":(.*)', content, re.DOTALL).group(1)).strip()

  output = clean_llm_output(m)

  print("!!!!output!!!!", output)

  if output.lower() == "no change":
    return None
  


  # print(content)
  # exit()
  
  # diff, description = content.split("=====")

  return Change(
    uri=seed.location['uri'],
    diff=output, 
    description="",
    temporal=seed.temporal,
  )

def clean_llm_output(llm_output: str):
  llm_output = llm_output.strip()
  
  if llm_output.startswith('```diff'):
    llm_output = llm_output[len('```diff'):len(llm_output)-len('```')]
  elif llm_output.startswith('```'):
    llm_output = llm_output.strip('```')

  if not llm_output.endswith('\n'):
    llm_output += "\n"
  
  return llm_output