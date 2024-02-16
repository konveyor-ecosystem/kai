/*! For license information please see 381.956b67fc.chunk.js.LICENSE.txt */
"use strict";
(self.webpackChunkkonveyor_static_report =
  self.webpackChunkkonveyor_static_report || []).push([
  [381],
  {
    79381: (e, t, n) => {
      n.r(t), n.d(t, { conf: () => u, language: () => p });
      var o,
        a,
        i = n(16599),
        r = Object.defineProperty,
        c = Object.getOwnPropertyDescriptor,
        l = Object.getOwnPropertyNames,
        m = Object.prototype.hasOwnProperty,
        d = (e, t, n, o) => {
          if ((t && "object" === typeof t) || "function" === typeof t)
            for (let a of l(t))
              m.call(e, a) ||
                a === n ||
                r(e, a, {
                  get: () => t[a],
                  enumerable: !(o = c(t, a)) || o.enumerable,
                });
          return e;
        },
        s = {};
      d(s, (o = i), "default"), a && d(a, o, "default");
      var u = {
          comments: { blockComment: ["\x3c!--", "--\x3e"] },
          brackets: [["<", ">"]],
          autoClosingPairs: [
            { open: "<", close: ">" },
            { open: "'", close: "'" },
            { open: '"', close: '"' },
          ],
          surroundingPairs: [
            { open: "<", close: ">" },
            { open: "'", close: "'" },
            { open: '"', close: '"' },
          ],
          onEnterRules: [
            {
              beforeText: new RegExp(
                "<([_:\\w][_:\\w-.\\d]*)([^/>]*(?!/)>)[^<]*$",
                "i",
              ),
              afterText: /^<\/([_:\w][_:\w-.\d]*)\s*>$/i,
              action: { indentAction: s.languages.IndentAction.IndentOutdent },
            },
            {
              beforeText: new RegExp(
                "<(\\w[\\w\\d]*)([^/>]*(?!/)>)[^<]*$",
                "i",
              ),
              action: { indentAction: s.languages.IndentAction.Indent },
            },
          ],
        },
        p = {
          defaultToken: "",
          tokenPostfix: ".xml",
          ignoreCase: !0,
          qualifiedName: /(?:[\w\.\-]+:)?[\w\.\-]+/,
          tokenizer: {
            root: [
              [/[^<&]+/, ""],
              { include: "@whitespace" },
              [
                /(<)(@qualifiedName)/,
                [{ token: "delimiter" }, { token: "tag", next: "@tag" }],
              ],
              [
                /(<\/)(@qualifiedName)(\s*)(>)/,
                [
                  { token: "delimiter" },
                  { token: "tag" },
                  "",
                  { token: "delimiter" },
                ],
              ],
              [
                /(<\?)(@qualifiedName)/,
                [{ token: "delimiter" }, { token: "metatag", next: "@tag" }],
              ],
              [
                /(<\!)(@qualifiedName)/,
                [{ token: "delimiter" }, { token: "metatag", next: "@tag" }],
              ],
              [/<\!\[CDATA\[/, { token: "delimiter.cdata", next: "@cdata" }],
              [/&\w+;/, "string.escape"],
            ],
            cdata: [
              [/[^\]]+/, ""],
              [/\]\]>/, { token: "delimiter.cdata", next: "@pop" }],
              [/\]/, ""],
            ],
            tag: [
              [/[ \t\r\n]+/, ""],
              [
                /(@qualifiedName)(\s*=\s*)("[^"]*"|'[^']*')/,
                ["attribute.name", "", "attribute.value"],
              ],
              [
                /(@qualifiedName)(\s*=\s*)("[^">?\/]*|'[^'>?\/]*)(?=[\?\/]\>)/,
                ["attribute.name", "", "attribute.value"],
              ],
              [
                /(@qualifiedName)(\s*=\s*)("[^">]*|'[^'>]*)/,
                ["attribute.name", "", "attribute.value"],
              ],
              [/@qualifiedName/, "attribute.name"],
              [/\?>/, { token: "delimiter", next: "@pop" }],
              [
                /(\/)(>)/,
                [{ token: "tag" }, { token: "delimiter", next: "@pop" }],
              ],
              [/>/, { token: "delimiter", next: "@pop" }],
            ],
            whitespace: [
              [/[ \t\r\n]+/, ""],
              [/<!--/, { token: "comment", next: "@comment" }],
            ],
            comment: [
              [/[^<\-]+/, "comment.content"],
              [/-->/, { token: "comment", next: "@pop" }],
              [/<!--/, "comment.content.invalid"],
              [/[<\-]/, "comment.content"],
            ],
          },
        };
    },
  },
]);
//# sourceMappingURL=381.956b67fc.chunk.js.map
