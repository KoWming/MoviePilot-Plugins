import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const Config_vue_vue_type_style_index_0_scoped_139e71ce_lang = '';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,mergeProps:_mergeProps,withModifiers:_withModifiers,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "plugin-config" };
const _hoisted_2 = { class: "setting-item d-flex align-center py-2" };
const _hoisted_3 = { class: "setting-content flex-grow-1" };
const _hoisted_4 = { class: "d-flex justify-space-between align-center" };
const _hoisted_5 = { class: "setting-item d-flex align-center py-2" };
const _hoisted_6 = { class: "setting-content flex-grow-1" };
const _hoisted_7 = { class: "d-flex justify-space-between align-center" };
const _hoisted_8 = { class: "setting-item d-flex align-center py-2" };
const _hoisted_9 = { class: "setting-content flex-grow-1" };
const _hoisted_10 = { class: "d-flex justify-space-between align-center" };
const _hoisted_11 = { class: "d-flex align-center px-3 py-2 mb-3 rounded bg-info-lighten-5" };

const {ref,reactive,onMounted} = await importShared('vue');



const _sfc_main = {
  __name: 'Config',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  },
  initialConfig: {
    type: Object,
    default: () => ({}),
  }
},
  emits: ['close', 'switch', 'config-updated-on-server', 'save'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

const form = ref(null);
const isFormValid = ref(true);
const error = ref(null);
const successMessage = ref(null);
const saving = ref(false);
const initialConfigLoaded = ref(false);
const loadingCookie = ref(false);

// 保存从服务器获取的配置，用于重置
const serverFetchedConfig = reactive({
  enabled: false,
  notify: false,
  cron: '',
  farm_interval: 5,
  use_proxy: false,
  retry_count: 3,
  cookie: '',
  onlyonce: false
});

// 编辑中的配置
const editableConfig = reactive({
  enabled: false,
  notify: false,
  cron: '',
  farm_interval: 5,
  use_proxy: false,
  retry_count: 3,
  cookie: '',
  onlyonce: false
});

// 更新编辑中的配置
const setEditableConfig = (sourceConfig) => {
  if (sourceConfig && typeof sourceConfig === 'object') {
    Object.keys(editableConfig).forEach(key => {
      if (sourceConfig.hasOwnProperty(key)) {
        editableConfig[key] = JSON.parse(JSON.stringify(sourceConfig[key]));
      }
    });
  }
};

const getPluginId = () => {
  return "VicomoFarm";
};

// 加载初始配置
async function loadInitialData() {
  error.value = null;
  saving.value = true;
  initialConfigLoaded.value = false;
  
  if (!props.initialConfig) { 
    error.value = '初始配置丢失，无法加载配置'; 
    saving.value = false; 
    return; 
  }
  
  try {
    const pluginId = getPluginId();
    if (!pluginId) ;
    
    const data = await props.api.get(`plugin/${pluginId}/config`);
    
    if (data) {
      setEditableConfig(data);
      Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(data)));
      initialConfigLoaded.value = true;
      successMessage.value = '当前配置已从服务器加载';
    } else {
      throw new Error('从服务器获取配置失败，使用宿主提供的初始配置');
    }
  } catch (err) {
    console.error('加载配置失败:', err);
    error.value = err.message || '加载配置失败，请检查网络或API';
    setEditableConfig(props.initialConfig);
    Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(props.initialConfig)));
    successMessage.value = null;
  } finally {
    saving.value = false;
    setTimeout(() => { successMessage.value = null; error.value = null; }, 4000);
  }
}

// 保存配置
async function saveFullConfig() {
  error.value = null;
  successMessage.value = null;
  if (!form.value) return;
  const validation = await form.value.validate();
  if (!validation.valid) {
    error.value = '请检查表单中的错误';
    return;
  }

  saving.value = true;

  try {
    // 设置onlyonce为false，确保兼容后端
    editableConfig.onlyonce = false;
    
    // 通过emit事件保存配置
    emit('save', JSON.parse(JSON.stringify(editableConfig)));
    successMessage.value = '配置已发送保存请求';
  } catch (err) {
    console.error('保存配置失败:', err);
    error.value = err.message || '保存配置失败，请检查网络或查看日志';
  } finally {
    saving.value = false;
    setTimeout(() => { 
      successMessage.value = null; 
      if (error.value && !error.value.startsWith('保存配置失败') && !error.value.startsWith('配置已部分保存')) { 
        error.value = null; 
      }
    }, 5000); 
  }
}

// 重置配置
function resetConfigToFetched() {
  if (initialConfigLoaded.value) {
    setEditableConfig(serverFetchedConfig);
    error.value = null;
    successMessage.value = '配置已重置为上次从服务器加载的状态';
    if (form.value) form.value.resetValidation();
  } else {
    error.value = '尚未从服务器加载配置，无法重置';
  }
  setTimeout(() => { successMessage.value = null; error.value = null; }, 3000);
}

async function fillWithSiteCookie() {
  error.value = null;
  successMessage.value = null;
  loadingCookie.value = true;
  
  try {
    const pluginId = getPluginId();
    const response = await props.api.get(`plugin/${pluginId}/cookie`);
    
    if (response && response.success) {
      if (typeof response.cookie === 'string' && response.cookie.trim().toLowerCase() === 'cookie') {
        throw new Error('站点Cookie无效，请在站点管理中配置真实Cookie');
      }
      editableConfig.cookie = response.cookie;
      successMessage.value = '已成功获取站点Cookie';
    } else {
      throw new Error(response?.msg || '获取站点Cookie失败');
    }
  } catch (err) {
    console.error('获取站点Cookie失败:', err);
    error.value = err.message || '获取站点Cookie失败，请检查站点配置';
  } finally {
    loadingCookie.value = false;
    setTimeout(() => { successMessage.value = null; error.value = null; }, 3000);
  }
}

onMounted(() => {
  // 使用初始配置显示，然后从服务器获取
  setEditableConfig(props.initialConfig);
  Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(props.initialConfig)));
  
  loadInitialData();
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_progress_circular = _resolveComponent("v-progress-circular");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_tooltip = _resolveComponent("v-tooltip");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_VCronField = _resolveComponent("VCronField");
  const _component_v_form = _resolveComponent("v-form");
  const _component_v_divider = _resolveComponent("v-divider");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_card_actions = _resolveComponent("v-card-actions");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_v_card, {
      flat: "",
      class: "rounded border"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_icon, {
              icon: "mdi-cog",
              class: "mr-2",
              color: "primary",
              size: "small"
            }),
            _cache[10] || (_cache[10] = _createElementVNode("span", null, "象岛农场配置", -1))
          ]),
          _: 1
        }),
        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
          default: _withCtx(() => [
            (error.value)
              ? (_openBlock(), _createBlock(_component_v_alert, {
                  key: 0,
                  type: "error",
                  density: "compact",
                  class: "mb-2 text-caption",
                  variant: "tonal",
                  closable: ""
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(error.value), 1)
                  ]),
                  _: 1
                }))
              : _createCommentVNode("", true),
            (successMessage.value)
              ? (_openBlock(), _createBlock(_component_v_alert, {
                  key: 1,
                  type: "success",
                  density: "compact",
                  class: "mb-2 text-caption",
                  variant: "tonal",
                  closable: ""
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(successMessage.value), 1)
                  ]),
                  _: 1
                }))
              : _createCommentVNode("", true),
            _createVNode(_component_v_form, {
              ref_key: "form",
              ref: form,
              modelValue: isFormValid.value,
              "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((isFormValid).value = $event)),
              onSubmit: _withModifiers(saveFullConfig, ["prevent"])
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card, {
                  flat: "",
                  class: "rounded mb-3 border config-card"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-tune",
                          class: "mr-2",
                          color: "primary",
                          size: "small"
                        }),
                        _cache[11] || (_cache[11] = _createElementVNode("span", null, "基本设置", -1))
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
                                _createElementVNode("div", _hoisted_2, [
                                  _createVNode(_component_v_icon, {
                                    icon: "mdi-power",
                                    size: "small",
                                    color: editableConfig.enabled ? 'success' : 'grey',
                                    class: "mr-3"
                                  }, null, 8, ["color"]),
                                  _createElementVNode("div", _hoisted_3, [
                                    _createElementVNode("div", _hoisted_4, [
                                      _cache[12] || (_cache[12] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用插件"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "是否启用象岛农场插件")
                                      ], -1)),
                                      _createVNode(_component_v_switch, {
                                        modelValue: editableConfig.enabled,
                                        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((editableConfig.enabled) = $event)),
                                        color: "primary",
                                        inset: "",
                                        disabled: saving.value,
                                        density: "compact",
                                        "hide-details": "",
                                        class: "small-switch"
                                      }, null, 8, ["modelValue", "disabled"])
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
                                _createElementVNode("div", _hoisted_5, [
                                  _createVNode(_component_v_icon, {
                                    icon: "mdi-bell",
                                    size: "small",
                                    color: editableConfig.notify ? 'info' : 'grey',
                                    class: "mr-3"
                                  }, null, 8, ["color"]),
                                  _createElementVNode("div", _hoisted_6, [
                                    _createElementVNode("div", _hoisted_7, [
                                      _cache[13] || (_cache[13] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用通知"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "完成后发送消息通知")
                                      ], -1)),
                                      _createVNode(_component_v_switch, {
                                        modelValue: editableConfig.notify,
                                        "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((editableConfig.notify) = $event)),
                                        color: "info",
                                        inset: "",
                                        disabled: saving.value,
                                        density: "compact",
                                        "hide-details": "",
                                        class: "small-switch"
                                      }, null, 8, ["modelValue", "disabled"])
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
                                    icon: "mdi-proxy",
                                    size: "small",
                                    color: editableConfig.use_proxy ? 'info' : 'grey',
                                    class: "mr-3"
                                  }, null, 8, ["color"]),
                                  _createElementVNode("div", _hoisted_9, [
                                    _createElementVNode("div", _hoisted_10, [
                                      _cache[14] || (_cache[14] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "使用代理"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "是否使用系统代理访问")
                                      ], -1)),
                                      _createVNode(_component_v_switch, {
                                        modelValue: editableConfig.use_proxy,
                                        "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((editableConfig.use_proxy) = $event)),
                                        color: "info",
                                        inset: "",
                                        disabled: saving.value,
                                        density: "compact",
                                        "hide-details": "",
                                        class: "small-switch"
                                      }, null, 8, ["modelValue", "disabled"])
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
                  class: "rounded mb-3 border config-card"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-clock-time-five",
                          class: "mr-2",
                          color: "primary",
                          size: "small"
                        }),
                        _cache[15] || (_cache[15] = _createElementVNode("span", null, "执行设置", -1))
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_row, null, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_col, {
                              cols: "12",
                              md: "6"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_text_field, {
                                  modelValue: editableConfig.cookie,
                                  "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((editableConfig.cookie) = $event)),
                                  label: "Cookie",
                                  type: "password",
                                  variant: "outlined",
                                  hint: "象岛农场的Cookie，用于访问网站",
                                  "persistent-hint": "",
                                  "prepend-inner-icon": "mdi-cookie",
                                  disabled: saving.value,
                                  density: "compact",
                                  class: "text-caption"
                                }, {
                                  "append-inner": _withCtx(() => [
                                    _createVNode(_component_v_tooltip, {
                                      location: "top",
                                      "open-delay": 500
                                    }, {
                                      activator: _withCtx(({ props }) => [
                                        _createVNode(_component_v_btn, _mergeProps(props, {
                                          icon: "",
                                          variant: "tonal",
                                          color: "secondary",
                                          onClick: fillWithSiteCookie,
                                          disabled: saving.value || loadingCookie.value,
                                          size: "small",
                                          class: "ml-1"
                                        }), {
                                          default: _withCtx(() => [
                                            (!loadingCookie.value)
                                              ? (_openBlock(), _createBlock(_component_v_icon, {
                                                  key: 0,
                                                  color: "secondary",
                                                  size: "small"
                                                }, {
                                                  default: _withCtx(() => _cache[16] || (_cache[16] = [
                                                    _createTextVNode("mdi-content-paste")
                                                  ])),
                                                  _: 1
                                                }))
                                              : (_openBlock(), _createBlock(_component_v_progress_circular, {
                                                  key: 1,
                                                  indeterminate: "",
                                                  size: "16",
                                                  width: "2",
                                                  color: "primary"
                                                }))
                                          ]),
                                          _: 2
                                        }, 1040, ["disabled"])
                                      ]),
                                      default: _withCtx(() => [
                                        _cache[17] || (_cache[17] = _createElementVNode("div", { class: "custom-tooltip-content" }, [
                                          _createElementVNode("span", { class: "text-caption" }, "使用已添加站点的Cookie")
                                        ], -1))
                                      ]),
                                      _: 1
                                    })
                                  ]),
                                  _: 1
                                }, 8, ["modelValue", "disabled"])
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_v_col, {
                              cols: "12",
                              md: "6"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_VCronField, {
                                  modelValue: editableConfig.cron,
                                  "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((editableConfig.cron) = $event)),
                                  label: "Cron表达式",
                                  hint: "设置执行周期，如：30 8 * * * (每天凌晨8:30)",
                                  "persistent-hint": "",
                                  density: "compact"
                                }, null, 8, ["modelValue"])
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_v_col, {
                              cols: "12",
                              md: "6"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_text_field, {
                                  modelValue: editableConfig.farm_interval,
                                  "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((editableConfig.farm_interval) = $event)),
                                  modelModifiers: { number: true },
                                  label: "重试间隔(秒)",
                                  type: "number",
                                  variant: "outlined",
                                  min: 1,
                                  max: 60,
                                  rules: [v => v === null || v === '' || (Number.isInteger(Number(v)) && Number(v) >= 1 && Number(v) <= 60) || '必须是1-60之间的整数'],
                                  hint: "失败重试的间隔时间",
                                  "persistent-hint": "",
                                  "prepend-inner-icon": "mdi-timer",
                                  disabled: saving.value,
                                  density: "compact",
                                  class: "text-caption"
                                }, null, 8, ["modelValue", "rules", "disabled"])
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_v_col, {
                              cols: "12",
                              md: "6"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_text_field, {
                                  modelValue: editableConfig.retry_count,
                                  "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((editableConfig.retry_count) = $event)),
                                  modelModifiers: { number: true },
                                  label: "重试次数",
                                  type: "number",
                                  variant: "outlined",
                                  min: 0,
                                  max: 5,
                                  rules: [v => v === null || v === '' || (Number.isInteger(Number(v)) && Number(v) >= 0 && Number(v) <= 5) || '必须是0-5之间的整数'],
                                  hint: "请求失败时的重试次数",
                                  "persistent-hint": "",
                                  "prepend-inner-icon": "mdi-refresh",
                                  disabled: saving.value,
                                  density: "compact",
                                  class: "text-caption"
                                }, null, 8, ["modelValue", "rules", "disabled"])
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
                _createElementVNode("div", _hoisted_11, [
                  _createVNode(_component_v_icon, {
                    icon: "mdi-information",
                    color: "info",
                    class: "mr-2",
                    size: "small"
                  }),
                  _cache[18] || (_cache[18] = _createElementVNode("span", { class: "text-caption" }, " 此插件用于监听象岛农场相关信息，支持定时执行、代理访问、失败重试等功能。 获取象岛农场信息，建议根据实际情况调整。 ", -1))
                ])
              ]),
              _: 1
            }, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_divider),
        _createVNode(_component_v_card_actions, { class: "px-2 py-1" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_btn, {
              color: "info",
              onClick: _cache[8] || (_cache[8] = $event => (emit('switch'))),
              "prepend-icon": "mdi-view-dashboard",
              disabled: saving.value,
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => _cache[19] || (_cache[19] = [
                _createTextVNode("状态页")
              ])),
              _: 1
            }, 8, ["disabled"]),
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              color: "secondary",
              variant: "text",
              onClick: resetConfigToFetched,
              disabled: !initialConfigLoaded.value || saving.value,
              "prepend-icon": "mdi-restore",
              size: "small"
            }, {
              default: _withCtx(() => _cache[20] || (_cache[20] = [
                _createTextVNode("重置")
              ])),
              _: 1
            }, 8, ["disabled"]),
            _createVNode(_component_v_btn, {
              color: "primary",
              disabled: !isFormValid.value || saving.value,
              onClick: saveFullConfig,
              loading: saving.value,
              "prepend-icon": "mdi-content-save",
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => _cache[21] || (_cache[21] = [
                _createTextVNode("保存配置")
              ])),
              _: 1
            }, 8, ["disabled", "loading"]),
            _createVNode(_component_v_btn, {
              color: "grey",
              onClick: _cache[9] || (_cache[9] = $event => (emit('close'))),
              "prepend-icon": "mdi-close",
              disabled: saving.value,
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => _cache[22] || (_cache[22] = [
                _createTextVNode("关闭")
              ])),
              _: 1
            }, 8, ["disabled"])
          ]),
          _: 1
        })
      ]),
      _: 1
    })
  ]))
}
}

};
const ConfigComponent = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-139e71ce"]]);

export { ConfigComponent as default };
