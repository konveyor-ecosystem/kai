"use strict";
(self.webpackChunkkonveyor_static_report =
  self.webpackChunkkonveyor_static_report || []).push([
  [472],
  {
    96472: (e, t, s) => {
      s.r(t), s.d(t, { default: () => L });
      var a = s(72791),
        n = s(16871),
        l = s(27054),
        c = s(75971),
        i = s(31994);
      const r = "pf-v5-l-gallery",
        m = { gutter: "pf-m-gutter" },
        o = (e) => {
          var {
              children: t = null,
              className: s = "",
              component: n = "div",
              hasGutter: l = !1,
              minWidths: o,
              maxWidths: d,
            } = e,
            p = (0, c.__rest)(e, [
              "children",
              "className",
              "component",
              "hasGutter",
              "minWidths",
              "maxWidths",
            ]);
          const h = {},
            f = n;
          o &&
            Object.entries(o || {}).map((e) => {
              let [t, s] = e;
              return (h[
                "--pf-v5-l-gallery--GridTemplateColumns--min".concat(
                  "default" !== t ? "-on-".concat(t) : "",
                )
              ] = s);
            });
          const u = {};
          d &&
            Object.entries(d || {}).map((e) => {
              let [t, s] = e;
              return (u[
                "--pf-v5-l-gallery--GridTemplateColumns--max".concat(
                  "default" !== t ? "-on-".concat(t) : "",
                )
              ] = s);
            });
          const y = Object.assign(Object.assign({}, h), u);
          return a.createElement(
            f,
            Object.assign(
              { className: (0, i.i)(r, l && m.gutter, s) },
              p,
              (o || d) && {
                style: Object.assign(Object.assign({}, y), p.style),
              },
            ),
            t,
          );
        };
      o.displayName = "Gallery";
      const d = (e) => {
        var { children: t = null, component: s = "div" } = e,
          n = (0, c.__rest)(e, ["children", "component"]);
        const l = s;
        return a.createElement(l, Object.assign({}, n), t);
      };
      d.displayName = "GalleryItem";
      var p = s(38625),
        h = s(66872),
        f = s(61088),
        u = s(41262),
        y = s(5120),
        g = s(95665),
        v = s(7233);
      const x = (0, s(39720).I)({
        name: "InfoAltIcon",
        height: 1024,
        width: 1024,
        svgPath:
          "M592,369 L592,289 C592.013862,284.755109 590.320137,280.682962 587.3,277.7 C584.338831,274.647672 580.252355,272.947987 576,273 L464,273 C459.755109,272.986138 455.682962,274.679863 452.7,277.7 C449.647672,280.661169 447.947987,284.747645 447.99884,289 L447.99884,369 C447.986138,373.244891 449.679863,377.317038 452.7,380.3 C455.661169,383.352328 459.747645,385.052013 464,385 L576,385 C580.244891,385.013862 584.317038,383.320137 587.3,380.3 C590.359349,377.343612 592.060354,373.253963 592,369 Z M592,705 L592,465 C592,456.163444 584.836556,449 576,449 L432,449 C423.163444,449 416,456.163444 416,465 L416,497 C416,505.836556 423.163444,513 432,513 L448,513 L448,705 L416,705 C407.163444,705 400,712.163444 400,721 L400,753 C400,761.836556 407.163444,769 416,769 L624,769 C632.836556,769 640,761.836556 640,753 L640,721 C640,712.163444 632.836556,705 624,705 L592,705 Z M512,896 C300.2,896 128,723.9 128,512 C128,300.3 300.2,128 512,128 C723.8,128 896,300.2 896,512 C896,723.8 723.7,896 512,896 Z M512.1,0 C229.7,0 0,229.8 0,512 C0,794.2 229.8,1024 512.1,1024 C794.4,1024 1024,794.3 1024,512 C1024,229.7 794.4,0 512.1,0 Z",
        yOffset: 0,
        xOffset: 0,
      });
      var C = s(49384),
        j = s(70494),
        _ = s(86257),
        b = s(7155),
        N = s(80184);
      const L = () => {
        const e = (0, n.bx)(),
          t = (0, a.useMemo)(
            () => (null === e || void 0 === e ? void 0 : e.tags) || [],
            [e],
          ).reduce(
            (e, t) => (
              (e[t.category.name] = e[t.category.name]
                ? [...e[t.category.name], t.name]
                : [t.name]),
              e
            ),
            {},
          );
        return (0, N.jsx)(N.Fragment, {
          children: (0, N.jsx)(l.NP, {
            children: (0, N.jsx)(o, {
              hasGutter: !0,
              minWidths: { md: "400px" },
              children: Object.entries(t).map((e, t) => {
                let [s, a] = e;
                return (0, N.jsx)(
                  d,
                  {
                    children: (0, N.jsxs)(p.Z, {
                      isFullHeight: !0,
                      children: [
                        (0, N.jsx)(h.l, { children: s }),
                        (0, N.jsx)(f.i, {}),
                        (0, N.jsx)(u.e, {
                          children: (0, N.jsx)(C.i, {
                            variant: "compact",
                            borders: !1,
                            children: (0, N.jsx)(j.p, {
                              children:
                                a.length > 0
                                  ? a.map((e, t) =>
                                      (0, N.jsx)(
                                        _.Tr,
                                        {
                                          children: (0, N.jsx)(b.Td, {
                                            children: e,
                                          }),
                                        },
                                        t,
                                      ),
                                    )
                                  : (0, N.jsxs)(y.u, {
                                      variant: y.I.sm,
                                      children: [
                                        (0, N.jsx)(g.k, { icon: x }),
                                        (0, N.jsx)(v.D, {
                                          headingLevel: "h4",
                                          size: "md",
                                          children: "No data to show",
                                        }),
                                      ],
                                    }),
                            }),
                          }),
                        }),
                      ],
                    }),
                  },
                  t,
                );
              }),
            }),
          }),
        });
      };
    },
    5120: (e, t, s) => {
      s.d(t, { I: () => a, u: () => r });
      var a,
        n = s(75971),
        l = s(72791),
        c = s(31994),
        i = s(50060);
      !(function (e) {
        (e.xs = "xs"),
          (e.sm = "sm"),
          (e.lg = "lg"),
          (e.xl = "xl"),
          (e.full = "full");
      })(a || (a = {}));
      const r = (e) => {
        var {
            children: t,
            className: s,
            variant: r = a.full,
            isFullHeight: m,
          } = e,
          o = (0, n.__rest)(e, [
            "children",
            "className",
            "variant",
            "isFullHeight",
          ]);
        return l.createElement(
          "div",
          Object.assign(
            {
              className: (0, c.i)(
                i.Z.emptyState,
                "xs" === r && i.Z.modifiers.xs,
                "sm" === r && i.Z.modifiers.sm,
                "lg" === r && i.Z.modifiers.lg,
                "xl" === r && i.Z.modifiers.xl,
                m && i.Z.modifiers.fullHeight,
                s,
              ),
            },
            o,
          ),
          l.createElement(
            "div",
            { className: (0, c.i)(i.Z.emptyStateContent) },
            t,
          ),
        );
      };
      r.displayName = "EmptyState";
    },
    95665: (e, t, s) => {
      s.d(t, { k: () => r });
      var a = s(75971),
        n = s(72791),
        l = s(31994),
        c = s(50060),
        i = s(30073);
      const r = (e) => {
        var { className: t, icon: s, color: r } = e,
          m = (0, a.__rest)(e, ["className", "icon", "color"]);
        const o = n.createElement(s, null).type === i.$;
        return n.createElement(
          "div",
          Object.assign(
            { className: (0, l.i)(c.Z.emptyStateIcon) },
            r && !o && { style: { "--pf-v5-c-empty-state__icon--Color": r } },
          ),
          n.createElement(
            s,
            Object.assign({ className: t, "aria-hidden": !o }, m),
          ),
        );
      };
      r.displayName = "EmptyStateIcon";
    },
    50060: (e, t, s) => {
      s.d(t, { Z: () => a });
      const a = {
        emptyState: "pf-v5-c-empty-state",
        emptyStateActions: "pf-v5-c-empty-state__actions",
        emptyStateBody: "pf-v5-c-empty-state__body",
        emptyStateContent: "pf-v5-c-empty-state__content",
        emptyStateFooter: "pf-v5-c-empty-state__footer",
        emptyStateIcon: "pf-v5-c-empty-state__icon",
        emptyStateTitleText: "pf-v5-c-empty-state__title-text",
        modifiers: {
          xs: "pf-m-xs",
          sm: "pf-m-sm",
          lg: "pf-m-lg",
          xl: "pf-m-xl",
          fullHeight: "pf-m-full-height",
        },
      };
    },
  },
]);
//# sourceMappingURL=472.07d81745.chunk.js.map
