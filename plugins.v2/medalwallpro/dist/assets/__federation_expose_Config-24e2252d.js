import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,Transition:_Transition,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,createElementBlock:_createElementBlock} = await importShared('vue');

const _hoisted_1 = { class: "plugin-config" };
const _hoisted_2 = { style: { "position": "absolute", "top": "0", "left": "0", "right": "0", "z-index": "50", "padding": "0 10px 10px 10px" } };
const _hoisted_3 = { class: "setting-item d-flex align-center py-2" };
const _hoisted_4 = { class: "setting-content flex-grow-1" };
const _hoisted_5 = { class: "d-flex align-center justify-space-between w-100" };
const _hoisted_6 = {
  class: "switch",
  style: { "--switch-checked-bg": "#bc98fd" }
};
const _hoisted_7 = ["disabled"];
const _hoisted_8 = { class: "setting-item d-flex align-center py-2" };
const _hoisted_9 = { class: "setting-content flex-grow-1" };
const _hoisted_10 = { class: "d-flex align-center justify-space-between w-100" };
const _hoisted_11 = {
  class: "switch",
  style: { "--switch-checked-bg": "#73cffe" }
};
const _hoisted_12 = ["disabled"];
const _hoisted_13 = { class: "setting-item d-flex align-center py-2" };
const _hoisted_14 = { class: "setting-content flex-grow-1" };
const _hoisted_15 = { class: "d-flex align-center justify-space-between w-100" };
const _hoisted_16 = {
  class: "switch",
  style: { "--switch-checked-bg": "#9adf66" }
};
const _hoisted_17 = ["disabled"];
const _hoisted_18 = { class: "text-caption text-grey mr-1 d-none d-sm-inline" };
const _hoisted_19 = { class: "d-none d-sm-inline" };
const _hoisted_20 = { class: "mt-4 pa-3 rounded text-caption d-flex flex-column notice-card" };
const _hoisted_21 = { class: "d-flex align-center mb-2" };
const _hoisted_22 = { class: "d-flex align-center" };
const {ref,onMounted,reactive,watch,computed} = await importShared('vue');

const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Config",
  props: {
    initialConfig: {
      type: Object,
      default: () => ({})
    },
    api: {
      type: Object,
      default: () => {
      }
    }
  },
  emits: ["save", "close", "switch"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const config = reactive({
      enabled: false,
      cron: "0 9 * * *",
      notify: false,
      chat_sites: [],
      use_proxy: true,
      retry_times: 3,
      retry_interval: 5
    });
    const originalConfig = reactive({});
    const siteOptions = ref([]);
    const saving = ref(false);
    const successMessage = ref("");
    const errorMessage = ref("");
    onMounted(async () => {
      if (props.initialConfig && Object.keys(props.initialConfig).length > 0) {
        Object.assign(config, props.initialConfig);
        Object.assign(originalConfig, JSON.parse(JSON.stringify(config)));
      }
      await fetchSites();
    });
    watch(() => props.initialConfig, (newVal) => {
      if (newVal && Object.keys(newVal).length > 0) {
        Object.assign(config, newVal);
        if (Object.keys(originalConfig).length === 0) {
          Object.assign(originalConfig, JSON.parse(JSON.stringify(newVal)));
        }
      }
    }, { deep: true });
    async function fetchSites() {
      try {
        const data = await props.api.get("plugin/MedalWallPro/sites");
        if (data) {
          siteOptions.value = data;
        }
      } catch (e) {
        console.error("Failed to fetch sites", e);
        showNotification("获取站点列表失败", "error");
      }
    }
    async function saveConfig() {
      saving.value = true;
      try {
        const res = await props.api.post("plugin/MedalWallPro/config", config);
        if (res && res.success) {
          showNotification("配置已保存", "success");
          emit("save", config);
          Object.assign(originalConfig, JSON.parse(JSON.stringify(config)));
        } else {
          showNotification(res?.message || "保存失败", "error");
        }
      } catch (e) {
        console.error("Failed to save config", e);
        showNotification("保存配置失败: " + (e.message || "未知错误"), "error");
      } finally {
        saving.value = false;
      }
    }
    function resetConfig() {
      if (Object.keys(originalConfig).length > 0) {
        Object.assign(config, JSON.parse(JSON.stringify(originalConfig)));
        showNotification("配置已重置", "success");
      }
    }
    function showNotification(message, type = "success") {
      if (type === "success") {
        successMessage.value = message;
        setTimeout(() => successMessage.value = "", 3e3);
      } else {
        errorMessage.value = message;
        setTimeout(() => errorMessage.value = "", 3e3);
      }
    }
    function notifyClose() {
      emit("close");
    }
    function notifySwitch() {
      emit("switch", "page");
    }
    const isAllSelected = computed(() => {
      return siteOptions.value.length > 0 && config.chat_sites.length === siteOptions.value.length;
    });
    const isPartiallySelected = computed(() => {
      return config.chat_sites.length > 0 && config.chat_sites.length < siteOptions.value.length;
    });
    const selectionIcon = computed(() => {
      if (isAllSelected.value) {
        return "mdi-checkbox-multiple-marked";
      } else if (isPartiallySelected.value) {
        return "mdi-minus-box-multiple-outline";
      } else {
        return "mdi-checkbox-multiple-blank-outline";
      }
    });
    const selectionText = computed(() => {
      return "全选";
    });
    function selectAllSites() {
      if (isAllSelected.value) {
        config.chat_sites = [];
      } else {
        config.chat_sites = siteOptions.value.map((site) => site.value);
      }
    }
    function clearAllSites() {
      config.chat_sites = [];
    }
    function invertSelection() {
      const allSiteValues = siteOptions.value.map((site) => site.value);
      const currentSelection = new Set(config.chat_sites);
      config.chat_sites = allSiteValues.filter((value) => !currentSelection.has(value));
    }
    return (_ctx, _cache) => {
      const _component_v_icon = _resolveComponent("v-icon");
      const _component_v_spacer = _resolveComponent("v-spacer");
      const _component_v_btn = _resolveComponent("v-btn");
      const _component_v_btn_group = _resolveComponent("v-btn-group");
      const _component_v_card_title = _resolveComponent("v-card-title");
      const _component_v_alert = _resolveComponent("v-alert");
      const _component_v_col = _resolveComponent("v-col");
      const _component_v_row = _resolveComponent("v-row");
      const _component_v_card_text = _resolveComponent("v-card-text");
      const _component_v_card = _resolveComponent("v-card");
      const _component_v_select = _resolveComponent("v-select");
      const _component_v_text_field = _resolveComponent("v-text-field");
      const _component_v_form = _resolveComponent("v-form");
      return _openBlock(), _createElementBlock("div", _hoisted_1, [
        _createVNode(_component_v_card, {
          flat: "",
          class: "rounded border"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center px-3 py-2 bg-gradient-primary" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-cog",
                  class: "mr-2",
                  color: "white",
                  size: "small"
                }),
                _cache[13] || (_cache[13] = _createElementVNode("span", { class: "text-white" }, "勋章墙配置", -1)),
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn_group, {
                  variant: "outlined",
                  density: "compact",
                  class: "mr-1"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: notifySwitch,
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
                        _cache[9] || (_cache[9] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "状态页", -1))
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: resetConfig,
                      disabled: saving.value,
                      size: "small",
                      "min-width": "40",
                      class: "px-0 px-sm-3"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-restore",
                          size: "18",
                          class: "mr-sm-1"
                        }),
                        _cache[10] || (_cache[10] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "重置", -1))
                      ]),
                      _: 1
                    }, 8, ["disabled"]),
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: saveConfig,
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
                        _cache[11] || (_cache[11] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "保存", -1))
                      ]),
                      _: 1
                    }, 8, ["loading"]),
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: notifyClose,
                      size: "small",
                      "min-width": "40",
                      class: "px-0 px-sm-3"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-close",
                          size: "18"
                        }),
                        _cache[12] || (_cache[12] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "关闭", -1))
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_text, {
              class: "px-3 py-3",
              style: { "position": "relative" }
            }, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_2, [
                  _createVNode(_Transition, { name: "slide-fade" }, {
                    default: _withCtx(() => [
                      successMessage.value ? (_openBlock(), _createBlock(_component_v_alert, {
                        key: 0,
                        type: "success",
                        density: "compact",
                        class: "mb-2 text-caption",
                        variant: "elevated",
                        closable: "",
                        "onClick:close": _cache[0] || (_cache[0] = ($event) => successMessage.value = "")
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(successMessage.value), 1)
                        ]),
                        _: 1
                      })) : _createCommentVNode("", true)
                    ]),
                    _: 1
                  }),
                  _createVNode(_Transition, { name: "slide-fade" }, {
                    default: _withCtx(() => [
                      errorMessage.value ? (_openBlock(), _createBlock(_component_v_alert, {
                        key: 0,
                        type: "error",
                        density: "compact",
                        class: "mb-2 text-caption",
                        variant: "elevated",
                        closable: "",
                        "onClick:close": _cache[1] || (_cache[1] = ($event) => errorMessage.value = "")
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(errorMessage.value), 1)
                        ]),
                        _: 1
                      })) : _createCommentVNode("", true)
                    ]),
                    _: 1
                  })
                ]),
                _createVNode(_component_v_form, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, {
                      flat: "",
                      class: "rounded mb-3 border inner-card"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_title, { class: "text-subtitle-2 px-3 py-2 bg-purple-lighten-5 d-flex align-center" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: "mdi-tune",
                              class: "mr-2",
                              color: "purple",
                              size: "small"
                            }),
                            _cache[14] || (_cache[14] = _createTextVNode(" 基础设置 ", -1))
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_row, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_col, {
                                  cols: "12",
                                  md: "4"
                                }, {
                                  default: _withCtx(() => [
                                    _createElementVNode("div", _hoisted_3, [
                                      _createVNode(_component_v_icon, {
                                        icon: "mdi-play-circle-outline",
                                        size: "small",
                                        color: config.enabled ? "success" : "grey",
                                        class: "mr-3"
                                      }, null, 8, ["color"]),
                                      _createElementVNode("div", _hoisted_4, [
                                        _createElementVNode("div", _hoisted_5, [
                                          _cache[16] || (_cache[16] = _createElementVNode("div", { class: "setting-text" }, [
                                            _createElementVNode("div", { class: "text-subtitle-2 font-weight-bold" }, "启用插件"),
                                            _createElementVNode("div", { class: "text-caption text-grey" }, "是否启用勋章墙插件")
                                          ], -1)),
                                          _createElementVNode("label", _hoisted_6, [
                                            _withDirectives(_createElementVNode("input", {
                                              "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => config.enabled = $event),
                                              type: "checkbox",
                                              disabled: saving.value
                                            }, null, 8, _hoisted_7), [
                                              [_vModelCheckbox, config.enabled]
                                            ]),
                                            _cache[15] || (_cache[15] = _createElementVNode("div", { class: "slider" }, [
                                              _createElementVNode("div", { class: "circle" })
                                            ], -1))
                                          ])
                                        ])
                                      ])
                                    ])
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_col, {
                                  cols: "12",
                                  md: "4"
                                }, {
                                  default: _withCtx(() => [
                                    _createElementVNode("div", _hoisted_8, [
                                      _createVNode(_component_v_icon, {
                                        icon: "mdi-message-processing-outline",
                                        size: "small",
                                        color: config.notify ? "info" : "grey",
                                        class: "mr-3"
                                      }, null, 8, ["color"]),
                                      _createElementVNode("div", _hoisted_9, [
                                        _createElementVNode("div", _hoisted_10, [
                                          _cache[18] || (_cache[18] = _createElementVNode("div", { class: "setting-text" }, [
                                            _createElementVNode("div", { class: "text-subtitle-2 font-weight-bold" }, "开启通知"),
                                            _createElementVNode("div", { class: "text-caption text-grey" }, "开启通知发送，首次运行不建议开启")
                                          ], -1)),
                                          _createElementVNode("label", _hoisted_11, [
                                            _withDirectives(_createElementVNode("input", {
                                              "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => config.notify = $event),
                                              type: "checkbox",
                                              disabled: saving.value
                                            }, null, 8, _hoisted_12), [
                                              [_vModelCheckbox, config.notify]
                                            ]),
                                            _cache[17] || (_cache[17] = _createElementVNode("div", { class: "slider" }, [
                                              _createElementVNode("div", { class: "circle" })
                                            ], -1))
                                          ])
                                        ])
                                      ])
                                    ])
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_col, {
                                  cols: "12",
                                  md: "4"
                                }, {
                                  default: _withCtx(() => [
                                    _createElementVNode("div", _hoisted_13, [
                                      _createVNode(_component_v_icon, {
                                        icon: "mdi-earth",
                                        size: "small",
                                        color: config.use_proxy ? "info" : "grey",
                                        class: "mr-3"
                                      }, null, 8, ["color"]),
                                      _createElementVNode("div", _hoisted_14, [
                                        _createElementVNode("div", _hoisted_15, [
                                          _cache[20] || (_cache[20] = _createElementVNode("div", { class: "setting-text" }, [
                                            _createElementVNode("div", { class: "text-subtitle-2 font-weight-bold" }, "使用代理"),
                                            _createElementVNode("div", { class: "text-caption text-grey" }, "使用系统代理连接站点")
                                          ], -1)),
                                          _createElementVNode("label", _hoisted_16, [
                                            _withDirectives(_createElementVNode("input", {
                                              "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => config.use_proxy = $event),
                                              type: "checkbox",
                                              disabled: saving.value
                                            }, null, 8, _hoisted_17), [
                                              [_vModelCheckbox, config.use_proxy]
                                            ]),
                                            _cache[19] || (_cache[19] = _createElementVNode("div", { class: "slider" }, [
                                              _createElementVNode("div", { class: "circle" })
                                            ], -1))
                                          ])
                                        ])
                                      ])
                                    ])
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_card, {
                      flat: "",
                      class: "rounded mb-3 border inner-card"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_title, { class: "text-subtitle-2 px-3 py-2 bg-blue-lighten-5 d-flex align-center" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: "mdi-eye-outline",
                              class: "mr-2",
                              color: "blue",
                              size: "small"
                            }),
                            _cache[23] || (_cache[23] = _createTextVNode(" 监控配置 ", -1)),
                            _createVNode(_component_v_spacer),
                            _createElementVNode("span", _hoisted_18, "已选: " + _toDisplayString(config.chat_sites.length) + " / " + _toDisplayString(siteOptions.value.length), 1),
                            _createVNode(_component_v_btn_group, {
                              variant: "outlined",
                              density: "compact",
                              class: "quick-action-group"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_btn, {
                                  onClick: selectAllSites,
                                  size: "x-small",
                                  color: isAllSelected.value ? "grey" : "primary",
                                  class: "px-1 px-sm-2"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: selectionIcon.value,
                                      size: "16",
                                      class: "mr-sm-1"
                                    }, null, 8, ["icon"]),
                                    _createElementVNode("span", _hoisted_19, _toDisplayString(selectionText.value), 1)
                                  ]),
                                  _: 1
                                }, 8, ["color"]),
                                _createVNode(_component_v_btn, {
                                  onClick: invertSelection,
                                  size: "x-small",
                                  color: "purple",
                                  class: "px-1 px-sm-2"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-swap-horizontal-variant",
                                      size: "16",
                                      class: "mr-sm-1"
                                    }),
                                    _cache[21] || (_cache[21] = _createElementVNode("span", { class: "d-none d-sm-inline" }, "反选", -1))
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_btn, {
                                  onClick: clearAllSites,
                                  size: "x-small",
                                  color: "red-lighten-1",
                                  class: "px-1 px-sm-2"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-close-box-multiple",
                                      size: "16",
                                      class: "mr-sm-1"
                                    }),
                                    _cache[22] || (_cache[22] = _createElementVNode("span", { class: "d-none d-sm-inline" }, "清空", -1))
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_row, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_col, { cols: "12" }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_select, {
                                      modelValue: config.chat_sites,
                                      "onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => config.chat_sites = $event),
                                      items: siteOptions.value,
                                      label: "监控站点",
                                      multiple: "",
                                      chips: "",
                                      "item-title": "title",
                                      "item-value": "value",
                                      variant: "outlined",
                                      density: "compact",
                                      "hide-details": "auto",
                                      color: "primary",
                                      hint: "选择需要监控勋章的站点",
                                      "persistent-hint": ""
                                    }, null, 8, ["modelValue", "items"])
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_col, {
                                  cols: "12",
                                  md: "4"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_text_field, {
                                      modelValue: config.cron,
                                      "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => config.cron = $event),
                                      label: "CRON表达式",
                                      placeholder: "0 9 * * *",
                                      variant: "outlined",
                                      density: "compact",
                                      "hide-details": "auto",
                                      color: "primary",
                                      prefix: "周期间隔"
                                    }, null, 8, ["modelValue"])
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_col, {
                                  cols: "12",
                                  md: "4"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_select, {
                                      modelValue: config.retry_times,
                                      "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => config.retry_times = $event),
                                      label: "重试次数",
                                      items: [1, 2, 3, 5],
                                      variant: "outlined",
                                      density: "compact",
                                      "hide-details": "auto",
                                      color: "primary"
                                    }, null, 8, ["modelValue"])
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_col, {
                                  cols: "12",
                                  md: "4"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_select, {
                                      modelValue: config.retry_interval,
                                      "onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => config.retry_interval = $event),
                                      label: "重试间隔(秒)",
                                      items: [3, 5, 10, 15],
                                      variant: "outlined",
                                      density: "compact",
                                      "hide-details": "auto",
                                      color: "primary"
                                    }, null, 8, ["modelValue"])
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }),
                    _createElementVNode("div", _hoisted_20, [
                      _createElementVNode("div", _hoisted_21, [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-bell-off-outline",
                          size: "small",
                          class: "mr-2",
                          color: "primary"
                        }),
                        _cache[24] || (_cache[24] = _createElementVNode("span", null, "建议首次运行时不要开启通知，避免因同步历史数据导致通知刷屏。", -1))
                      ]),
                      _createElementVNode("div", _hoisted_22, [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-alert-circle-outline",
                          size: "small",
                          class: "mr-2",
                          color: "warning"
                        }),
                        _cache[25] || (_cache[25] = _createElementVNode("span", null, "站点图片如果无法显示可能是站点图床失效无法获取！", -1))
                      ])
                    ])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        })
      ]);
    };
  }
});

const Config_vue_vue_type_style_index_0_scoped_47308d1d_lang = '';

const Config = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-47308d1d"]]);

export { Config as default };
