import subprocess
import os
import re

from tree_sitter import Node, Language, Parser

def parse_gumtree_output(gumtree_output: str) -> list[dict]:
  output: list[dict] = []

  sections = gumtree_output.split('===\n')

  for section in filter(None, sections):
    pieces = section.split('---\n')
    if len(pieces) != 2: continue # TODO: Silently fail for now

    action, argument = pieces[0].strip(), pieces[1].strip()
    if action == 'match': continue

    arguments = argument.split('\n')

    type_tuple_pattern = r'^(.*?)\s\[(\d+),(\d+)\]$'
    at_pattern         = r'^(.*?)\s(\d+)$'
    replace_by_pattern = r'^replace\s(.*?)\sby\s(.*)$'

    m = re.search(type_tuple_pattern, arguments[0])
    if not m: continue

    node = {
      'type':       str(m.group(1)),
      'start_byte': int(m.group(2)),
      'end_byte':   int(m.group(3)),
    }

    # NOTE: gumtree returns some funky stuff in `type` with `update-node`
    if action == 'update-node':
      m = re.search(replace_by_pattern, arguments[-1])
      old, new = m.group(1), m.group(2)

      output.append({'action': action, 'node': node, 'old': old, 'new': new})

    elif action == 'insert-tree' or action == 'move-tree':
      m = re.search(type_tuple_pattern, arguments[-2])
      to = {
        'type':       str(m.group(1)),
        'start_byte': int(m.group(2)),
        'end_byte':   int(m.group(3)),
      }
      
      m = re.search(at_pattern, arguments[-1])
      at = int(m.group(2))

      output.append({'action': action, 'node': node, 'to': to, 'at': at})
     
    elif action == 'delete-node':
      output.append({'action': action, 'node': node})

    else:
      raise Exception('parse_gumtree_output: unhandled action')

  return output
  


gumtree_path = '/home/jonah/Projects/github.com/konveyor-ecosystem/kai/gumtree-3.1.0-SNAPSHOT/bin/gumtree'
before_path = '/home/jonah/Projects/kyma-prototyping/java-test-projects/complex-numbers/src/main/java/net/jsussman/inheritance/Simple.java'
after_path = '/home/jonah/Projects/kyma-prototyping/java-test-projects/complex-numbers/src/main/java/net/jsussman/inheritance/SimpleEdited.java'
tree_sitter_parser_path = '/home/jonah/Projects/github.com/konveyor-ecosystem/kai/tree-sitter-parser'

# env = os.environ.copy()
# env['PATH'] = tree_sitter_parser_path + ':' + os.environ.get('PATH')
# output = subprocess.run(
#   [gumtree_path, 'textdiff', before_path, after_path, '-g', 'java-treesitter'], 
#   stdout=subprocess.PIPE, 
#   env=env,
# ).stdout.decode()

# result = parse_gumtree_output(output)

# import pprint
# pprint.pprint(result)



TS_OUTPUT_PATH = "build/language-java.so"
TS_REPO_PATHS = ["../tree-sitter-java/"]
TS_NAME = "java"

Language.build_library(TS_OUTPUT_PATH, TS_REPO_PATHS)
TS_JAVA_LANGUAGE = Language(TS_OUTPUT_PATH, TS_NAME)

# PROJECT_PATH  = "/home/jonah/Projects/kyma-prototyping/java-test-projects/complex-numbers/"
PROJECT_PATH = "/home/jonah/Projects/github.com/konveyor-ecosystem/kai/phase-2/java-test-projects/complex-numbers/"

parser = Parser()
parser.set_language(TS_JAVA_LANGUAGE)

with open(before_path, 'r') as f:
  file_before = f.read()
tree_before = parser.parse(bytes(file_before, 'utf-8'))

with open(after_path, 'r') as f:
  file_after = f.read()
tree_after = parser.parse(bytes(file_after, 'utf-8'))

print(tree_before.root_node.children[1].children[1].child_by_field_name('name').text)
print(tree_before.root_node.children[4].child_by_field_name('body').named_children[0].sexp())
print(tree_before.root_node.children[4].child_by_field_name('body').named_children[0].child_by_field_name('declarator').end_point)
print(tree_before.root_node.children[4].child_by_field_name('body').named_children[0].child_by_field_name('declarator').sexp())
print(tree_before.root_node.children[4].child_by_field_name('body').named_children[0].child_by_field_name('declarator').start_byte)
print(tree_before.root_node.children[4].child_by_field_name('body').named_children[0].child_by_field_name('declarator').end_byte)

from codeplan import *
from monitors4codegen.multilspy.multilspy_config import MultilspyConfig
from monitors4codegen.multilspy.multilspy_logger import MultilspyLogger

LSP_CONFIG = MultilspyConfig.from_dict({"code_language": "java"})
LSP_LOGGER = MultilspyLogger()

LSP = LanguageServer.create(
  LSP_CONFIG, LSP_LOGGER, 
  PROJECT_PATH
)


async def do_it():
  async with LSP.start_server():
    ctx = CodePlanContext(
      language_server=LSP,
      repo_path=PROJECT_PATH,
      ts_language=TS_JAVA_LANGUAGE,
      gumtree_path=gumtree_path,
      tree_sitter_parser_path=tree_sitter_parser_path
    )


    uri = 'file:///home/jonah/Projects/github.com/konveyor-ecosystem/kai/phase-2/java-test-projects/complex-numbers/src/main/java/net/jsussman/dummyapp/ExampleClass.java'
    with open('/home/jonah/Projects/github.com/konveyor-ecosystem/kai/phase-2/ExampleClass.diff', 'r') as f:
      diff = f.read()

    change = Change(
      diff=diff,
      uri=uri,
      description="",
      temporal=TemporalContext(
        previous_changes=[]
      ),
    )

    print(await get_affected_blocks(ctx, change))

import asyncio
if __name__ == '__main__':
  asyncio.run(do_it())