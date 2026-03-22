import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,openBlock:_openBlock,createElementBlock:_createElementBlock,toDisplayString:_toDisplayString,mergeProps:_mergeProps,createBlock:_createBlock,createCommentVNode:_createCommentVNode} = await importShared('vue');

const _hoisted_1 = { class: "as-config" };
const _hoisted_2 = { class: "as-topbar" };
const _hoisted_3 = { class: "as-topbar__left" };
const _hoisted_4 = { class: "as-header__icon" };
const _hoisted_5 = {
  class: "as-topbar__right",
  style: { "padding": "2px" }
};
const _hoisted_6 = { class: "as-card" };
const _hoisted_7 = { class: "as-config-card__header" };
const _hoisted_8 = { class: "as-row__text" };
const _hoisted_9 = {
  class: "switch",
  style: { "--switch-checked-bg": "#8b5cf6" }
};
const _hoisted_10 = { class: "slider" };
const _hoisted_11 = { class: "circle" };
const _hoisted_12 = {
  class: "cross",
  "xml:space": "preserve",
  style: { "enable-background": "new 0 0 512 512" },
  viewBox: "0 0 365.696 365.696",
  y: "0",
  x: "0",
  height: "6",
  width: "6",
  "xmlns:xlink": "http://www.w3.org/1999/xlink",
  version: "1.1",
  xmlns: "http://www.w3.org/2000/svg"
};
const _hoisted_13 = {
  class: "checkmark",
  "xml:space": "preserve",
  style: { "enable-background": "new 0 0 512 512" },
  viewBox: "0 0 24 24",
  y: "0",
  x: "0",
  height: "10",
  width: "10",
  "xmlns:xlink": "http://www.w3.org/1999/xlink",
  version: "1.1",
  xmlns: "http://www.w3.org/2000/svg"
};
const _hoisted_14 = { class: "as-row__text" };
const _hoisted_15 = {
  class: "switch",
  style: { "--switch-checked-bg": "#10b981" }
};
const _hoisted_16 = { class: "slider" };
const _hoisted_17 = { class: "circle" };
const _hoisted_18 = {
  class: "cross",
  "xml:space": "preserve",
  style: { "enable-background": "new 0 0 512 512" },
  viewBox: "0 0 365.696 365.696",
  y: "0",
  x: "0",
  height: "6",
  width: "6",
  "xmlns:xlink": "http://www.w3.org/1999/xlink",
  version: "1.1",
  xmlns: "http://www.w3.org/2000/svg"
};
const _hoisted_19 = {
  class: "checkmark",
  "xml:space": "preserve",
  style: { "enable-background": "new 0 0 512 512" },
  viewBox: "0 0 24 24",
  y: "0",
  x: "0",
  height: "10",
  width: "10",
  "xmlns:xlink": "http://www.w3.org/1999/xlink",
  version: "1.1",
  xmlns: "http://www.w3.org/2000/svg"
};
const _hoisted_20 = {
  class: "as-field",
  style: { "margin-top": "12px", "margin-bottom": "8px" }
};
const _hoisted_21 = { class: "as-field__label mb-1" };
const _hoisted_22 = {
  class: "as-field",
  style: { "margin-top": "12px", "margin-bottom": "8px" }
};
const _hoisted_23 = { class: "as-card" };
const _hoisted_24 = {
  class: "as-config-card__header",
  style: { "background": "rgba(var(--v-theme-info), 0.08)", "color": "rgb(var(--v-theme-info))" }
};
const _hoisted_25 = { style: { "font-size": "13px", "line-height": "1.8", "color": "rgba(var(--v-theme-on-surface), 0.75)", "padding": "4px 0" } };
const _hoisted_26 = { class: "d-flex align-center gap-2 mb-1" };
const _hoisted_27 = {
  class: "d-flex align-center",
  style: { "margin-left": "4px" }
};
const {ref,reactive,watch} = await importShared('vue');

const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Config",
  props: {
    initialConfig: { type: Object, default: () => ({}) },
    api: { type: Object, default: () => ({}) }
  },
  emits: ["save", "close", "switch"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const config = reactive({
      enabled: false,
      notify: true,
      cron: "0 */6 * * *",
      mode: "closest",
      server_id: "",
      retry_count: 2,
      history_limit: 31,
      ...props.initialConfig
    });
    watch(
      () => props.initialConfig,
      (val) => Object.assign(config, val),
      { deep: true }
    );
    const modeOptions = [
      { title: "最近节点（自动）", value: "closest", icon: "mdi-earth", color: "primary" },
      { title: "中国电信", value: "telecom", icon: "mdi-lan-connect", color: "blue-darken-2" },
      { title: "中国联通", value: "unicom", icon: "mdi-web", color: "deep-orange" },
      { title: "中国移动", value: "mobile", icon: "mdi-signal-5g", color: "light-blue-darken-1" },
      { title: "固定节点", value: "fixed", icon: "mdi-pin", color: "grey" }
    ];
    const saving = ref(false);
    const snackbar = reactive({ show: false, text: "", color: "success" });
    async function handleSave() {
      saving.value = true;
      try {
        emit("save", { ...config });
        snackbar.text = "配置已保存";
        snackbar.color = "success";
        snackbar.show = true;
      } catch (e) {
        snackbar.text = "保存失败";
        snackbar.color = "error";
        snackbar.show = true;
      } finally {
        saving.value = false;
      }
    }
    return (_ctx, _cache) => {
      const _component_v_icon = _resolveComponent("v-icon");
      const _component_v_btn = _resolveComponent("v-btn");
      const _component_v_btn_group = _resolveComponent("v-btn-group");
      const _component_v_col = _resolveComponent("v-col");
      const _component_v_row = _resolveComponent("v-row");
      const _component_v_list_item = _resolveComponent("v-list-item");
      const _component_v_select = _resolveComponent("v-select");
      const _component_v_text_field = _resolveComponent("v-text-field");
      const _component_v_slide_x_reverse_transition = _resolveComponent("v-slide-x-reverse-transition");
      const _component_VCronField = _resolveComponent("VCronField");
      const _component_v_snackbar = _resolveComponent("v-snackbar");
      return _openBlock(), _createElementBlock("div", _hoisted_1, [
        _createElementVNode("div", _hoisted_2, [
          _createElementVNode("div", _hoisted_3, [
            _createElementVNode("div", _hoisted_4, [
              _createVNode(_component_v_icon, {
                icon: "mdi-cog",
                size: "24"
              })
            ]),
            _cache[10] || (_cache[10] = _createElementVNode("div", null, [
              _createElementVNode("div", { class: "as-header__title" }, "网络测速 · 配置"),
              _createElementVNode("div", { class: "as-header__sub" }, "AutoSpeed Plugin")
            ], -1))
          ]),
          _createElementVNode("div", _hoisted_5, [
            _createVNode(_component_v_btn_group, {
              variant: "tonal",
              density: "compact",
              class: "elevation-0"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  onClick: _cache[0] || (_cache[0] = ($event) => emit("switch", "page")),
                  size: "small",
                  "min-width": "40",
                  class: "px-0 px-sm-3"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_icon, {
                      icon: "mdi-view-dashboard",
                      size: "18",
                      class: "mr-sm-1"
                    }),
                    _cache[11] || (_cache[11] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "状态页", -1))
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_btn, {
                  color: "primary",
                  onClick: handleSave,
                  loading: saving.value,
                  size: "small",
                  "min-width": "40",
                  class: "px-0 px-sm-3"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_icon, {
                      icon: "mdi-content-save",
                      size: "18",
                      class: "mr-sm-1"
                    }),
                    _cache[12] || (_cache[12] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "保存", -1))
                  ]),
                  _: 1
                }, 8, ["loading"]),
                _createVNode(_component_v_btn, {
                  color: "primary",
                  onClick: _cache[1] || (_cache[1] = ($event) => emit("close")),
                  size: "small",
                  "min-width": "40",
                  class: "px-0 px-sm-3"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_icon, {
                      icon: "mdi-close",
                      size: "18"
                    }),
                    _cache[13] || (_cache[13] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "关闭", -1))
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ])
        ]),
        _createElementVNode("div", _hoisted_6, [
          _createElementVNode("div", _hoisted_7, [
            _createVNode(_component_v_icon, {
              icon: "mdi-tune-vertical",
              size: "18",
              class: "mr-2"
            }),
            _cache[14] || (_cache[14] = _createTextVNode("基础设置 ", -1))
          ]),
          _createVNode(_component_v_row, { class: "mt-1 mb-1" }, {
            default: _withCtx(() => [
              _createVNode(_component_v_col, {
                cols: "12",
                sm: "6",
                class: "d-flex align-center justify-space-between py-1"
              }, {
                default: _withCtx(() => [
                  _createElementVNode("span", _hoisted_8, [
                    _createVNode(_component_v_icon, {
                      icon: "mdi-power-plug",
                      size: "20",
                      color: config.enabled ? "primary" : "grey",
                      class: "mr-2"
                    }, null, 8, ["color"]),
                    _cache[15] || (_cache[15] = _createTextVNode("启用插件 ", -1))
                  ]),
                  _createElementVNode("label", _hoisted_9, [
                    _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => config.enabled = $event),
                      type: "checkbox"
                    }, null, 512), [
                      [_vModelCheckbox, config.enabled]
                    ]),
                    _createElementVNode("div", _hoisted_10, [
                      _createElementVNode("div", _hoisted_11, [
                        (_openBlock(), _createElementBlock("svg", _hoisted_12, [..._cache[16] || (_cache[16] = [
                          _createElementVNode("g", null, [
                            _createElementVNode("path", {
                              "data-original": "#000000",
                              fill: "currentColor",
                              d: "M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"
                            })
                          ], -1)
                        ])])),
                        (_openBlock(), _createElementBlock("svg", _hoisted_13, [..._cache[17] || (_cache[17] = [
                          _createElementVNode("g", null, [
                            _createElementVNode("path", {
                              class: "",
                              "data-original": "#000000",
                              fill: "currentColor",
                              d: "M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"
                            })
                          ], -1)
                        ])]))
                      ])
                    ])
                  ])
                ]),
                _: 1
              }),
              _createVNode(_component_v_col, {
                cols: "12",
                sm: "6",
                class: "d-flex align-center justify-space-between py-1"
              }, {
                default: _withCtx(() => [
                  _createElementVNode("span", _hoisted_14, [
                    _createVNode(_component_v_icon, {
                      icon: "mdi-bell-ring-outline",
                      size: "20",
                      color: config.notify ? "success" : "grey",
                      class: "mr-2"
                    }, null, 8, ["color"]),
                    _cache[18] || (_cache[18] = _createTextVNode("推送通知 ", -1))
                  ]),
                  _createElementVNode("label", _hoisted_15, [
                    _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => config.notify = $event),
                      type: "checkbox"
                    }, null, 512), [
                      [_vModelCheckbox, config.notify]
                    ]),
                    _createElementVNode("div", _hoisted_16, [
                      _createElementVNode("div", _hoisted_17, [
                        (_openBlock(), _createElementBlock("svg", _hoisted_18, [..._cache[19] || (_cache[19] = [
                          _createElementVNode("g", null, [
                            _createElementVNode("path", {
                              "data-original": "#000000",
                              fill: "currentColor",
                              d: "M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"
                            })
                          ], -1)
                        ])])),
                        (_openBlock(), _createElementBlock("svg", _hoisted_19, [..._cache[20] || (_cache[20] = [
                          _createElementVNode("g", null, [
                            _createElementVNode("path", {
                              class: "",
                              "data-original": "#000000",
                              fill: "currentColor",
                              d: "M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"
                            })
                          ], -1)
                        ])]))
                      ])
                    ])
                  ])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _cache[22] || (_cache[22] = _createElementVNode("div", { class: "as-divider" }, null, -1)),
          _createElementVNode("div", _hoisted_20, [
            _createElementVNode("label", _hoisted_21, [
              _createVNode(_component_v_icon, {
                icon: "mdi-wan",
                size: "18",
                color: "info",
                class: "mr-1"
              }),
              _cache[21] || (_cache[21] = _createTextVNode("节点选择模式 ", -1))
            ]),
            _createVNode(_component_v_row, { dense: "" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, {
                  cols: "12",
                  sm: config.mode === "fixed" ? 6 : 12,
                  style: { "transition": "all 0.3s ease" }
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_select, {
                      modelValue: config.mode,
                      "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => config.mode = $event),
                      items: modeOptions,
                      "item-title": "title",
                      "item-value": "value",
                      density: "compact",
                      variant: "outlined",
                      "hide-details": "auto",
                      class: "as-input"
                    }, {
                      selection: _withCtx(({ item }) => [
                        _createVNode(_component_v_icon, {
                          icon: item.raw.icon,
                          color: item.raw.color,
                          size: "18",
                          class: "mr-2"
                        }, null, 8, ["icon", "color"]),
                        _createTextVNode(" " + _toDisplayString(item.raw.title), 1)
                      ]),
                      item: _withCtx(({ props: props2, item }) => [
                        _createVNode(_component_v_list_item, _mergeProps(props2, {
                          title: item.raw.title
                        }), {
                          prepend: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: item.raw.icon,
                              color: item.raw.color,
                              size: "20",
                              class: "mr-3"
                            }, null, 8, ["icon", "color"])
                          ]),
                          _: 2
                        }, 1040, ["title"])
                      ]),
                      _: 1
                    }, 8, ["modelValue"])
                  ]),
                  _: 1
                }, 8, ["sm"]),
                config.mode === "fixed" ? (_openBlock(), _createBlock(_component_v_col, {
                  key: 0,
                  cols: "12",
                  sm: "6"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_slide_x_reverse_transition, { appear: "" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_text_field, {
                          modelValue: config.server_id,
                          "onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => config.server_id = $event),
                          label: "固定节点 ID",
                          placeholder: "例如: 3633",
                          density: "compact",
                          variant: "outlined",
                          "hide-details": "auto",
                          color: "primary",
                          hint: "输入 Speedtest 节点数字 ID",
                          "persistent-hint": ""
                        }, null, 8, ["modelValue"])
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })) : _createCommentVNode("", true)
              ]),
              _: 1
            })
          ]),
          _cache[23] || (_cache[23] = _createElementVNode("div", { class: "as-divider my-2" }, null, -1)),
          _createElementVNode("div", _hoisted_22, [
            _createVNode(_component_v_row, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "4"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_VCronField, {
                      modelValue: config.cron,
                      "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => config.cron = $event),
                      label: "Cron表达式",
                      hint: "周期，例如：0 */6 * * *",
                      "persistent-hint": "",
                      density: "compact"
                    }, null, 8, ["modelValue"])
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "4"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_text_field, {
                      modelValue: config.retry_count,
                      "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => config.retry_count = $event),
                      modelModifiers: { number: true },
                      label: "测速重试次数",
                      placeholder: "2",
                      type: "number",
                      density: "compact",
                      variant: "outlined",
                      "hide-details": "auto",
                      color: "primary",
                      hint: "失败时的最大重试次数",
                      "persistent-hint": "",
                      min: 0,
                      max: 10
                    }, null, 8, ["modelValue"])
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "4"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_text_field, {
                      modelValue: config.history_limit,
                      "onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => config.history_limit = $event),
                      modelModifiers: { number: true },
                      label: "历史保留条数",
                      placeholder: "31",
                      type: "number",
                      density: "compact",
                      variant: "outlined",
                      "hide-details": "auto",
                      color: "primary",
                      hint: "最多保留的历史数据条数",
                      "persistent-hint": "",
                      min: 10,
                      max: 5e3
                    }, null, 8, ["modelValue"])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ])
        ]),
        _createElementVNode("div", _hoisted_23, [
          _createElementVNode("div", _hoisted_24, [
            _createVNode(_component_v_icon, {
              icon: "mdi-heart-outline",
              size: "18",
              class: "mr-2"
            }),
            _cache[24] || (_cache[24] = _createTextVNode("致谢 ", -1))
          ]),
          _createElementVNode("div", _hoisted_25, [
            _createElementVNode("div", _hoisted_26, [
              _createVNode(_component_v_icon, {
                icon: "mdi-star-four-points",
                size: "14",
                color: "warning",
                class: "mr-1"
              }),
              _cache[25] || (_cache[25] = _createElementVNode("span", null, [
                _createTextVNode("本插件测速核心实现参考自 "),
                _createElementVNode("strong", null, "鱼丸粗面"),
                _createTextVNode(" 大佬的开源项目。")
              ], -1))
            ]),
            _createElementVNode("div", _hoisted_27, [
              _createVNode(_component_v_icon, {
                icon: "mdi-github",
                size: "16",
                class: "mr-2",
                style: { "opacity": "0.7" }
              }),
              _cache[26] || (_cache[26] = _createElementVNode("a", {
                href: "https://github.com/yuwancumian2009/Autospeed",
                target: "_blank",
                rel: "noopener noreferrer",
                class: "as-link"
              }, " yuwancumian2009 / Autospeed ", -1))
            ])
          ])
        ]),
        _createVNode(_component_v_snackbar, {
          modelValue: snackbar.show,
          "onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => snackbar.show = $event),
          color: snackbar.color,
          timeout: "2500",
          location: "top"
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(snackbar.text), 1)
          ]),
          _: 1
        }, 8, ["modelValue", "color"])
      ]);
    };
  }
});

const Config_vue_vue_type_style_index_0_scoped_4ddfd835_lang = '';

const Config = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-4ddfd835"]]);

export { Config as default };
