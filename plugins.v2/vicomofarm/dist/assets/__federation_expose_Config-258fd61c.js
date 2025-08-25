import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const CustomSwitch_vue_vue_type_style_index_0_scoped_68d07641_lang = '';

const {createElementVNode:_createElementVNode$1,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1} = await importShared('vue');


const _hoisted_1$1 = { class: "switch" };
const _hoisted_2$1 = ["checked", "disabled"];
const _hoisted_3$1 = { class: "slider" };
const _hoisted_4$1 = { class: "circle" };
const _hoisted_5$1 = {
  class: "cross",
  "xml:space": "preserve",
  style: {"enable-background":"new 0 0 512 512"},
  viewBox: "0 0 365.696 365.696",
  y: "0",
  x: "0",
  height: "6",
  width: "6",
  "xmlns:xlink": "http://www.w3.org/1999/xlink",
  version: "1.1",
  xmlns: "http://www.w3.org/2000/svg"
};
const _hoisted_6$1 = {
  class: "checkmark",
  "xml:space": "preserve",
  style: {"enable-background":"new 0 0 512 512"},
  viewBox: "0 0 24 24",
  y: "0",
  x: "0",
  height: "10",
  width: "10",
  "xmlns:xlink": "http://www.w3.org/1999/xlink",
  version: "1.1",
  xmlns: "http://www.w3.org/2000/svg"
};


const _sfc_main$1 = {
  __name: 'CustomSwitch',
  props: {
  modelValue: {
    type: Boolean,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  }
},
  emits: ['update:modelValue'],
  setup(__props) {





return (_ctx, _cache) => {
  return (_openBlock$1(), _createElementBlock$1("label", _hoisted_1$1, [
    _createElementVNode$1("input", {
      checked: __props.modelValue,
      type: "checkbox",
      onChange: _cache[0] || (_cache[0] = $event => (_ctx.$emit('update:modelValue', $event.target.checked))),
      disabled: __props.disabled
    }, null, 40, _hoisted_2$1),
    _createElementVNode$1("div", _hoisted_3$1, [
      _createElementVNode$1("div", _hoisted_4$1, [
        (_openBlock$1(), _createElementBlock$1("svg", _hoisted_5$1, _cache[1] || (_cache[1] = [
          _createElementVNode$1("g", null, [
            _createElementVNode$1("path", {
              "data-original": "#000000",
              fill: "currentColor",
              d: "M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"
            })
          ], -1)
        ]))),
        (_openBlock$1(), _createElementBlock$1("svg", _hoisted_6$1, _cache[2] || (_cache[2] = [
          _createElementVNode$1("g", null, [
            _createElementVNode$1("path", {
              class: "",
              "data-original": "#000000",
              fill: "currentColor",
              d: "M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"
            })
          ], -1)
        ])))
      ])
    ])
  ]))
}
}

};
const CustomSwitch = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-68d07641"]]);

const Config_vue_vue_type_style_index_0_scoped_7998ca2e_lang = '';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,Fragment:_Fragment,createElementBlock:_createElementBlock,withModifiers:_withModifiers} = await importShared('vue');


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
const _hoisted_11 = { class: "tooltip-container" };
const _hoisted_12 = { class: "setting-item d-flex align-center py-2 mb-5" };
const _hoisted_13 = { class: "setting-content flex-grow-1" };
const _hoisted_14 = { class: "d-flex justify-space-between align-center" };
const _hoisted_15 = { class: "setting-item d-flex align-center py-2 mb-5" };
const _hoisted_16 = { class: "setting-content flex-grow-1" };
const _hoisted_17 = { class: "d-flex justify-space-between align-center" };
const _hoisted_18 = { class: "setting-item d-flex align-center py-2 mb-5" };
const _hoisted_19 = { class: "setting-content flex-grow-1" };
const _hoisted_20 = { class: "d-flex justify-space-between align-center" };
const _hoisted_21 = {
  class: "d-flex align-center",
  style: {"gap":"16px","flex-wrap":"wrap"}
};
const _hoisted_22 = {
  class: "text-caption mb-4",
  style: {"color":"#999","margin-top":"5px","margin-bottom":"19px"}
};
const _hoisted_23 = { class: "d-flex align-center px-3 py-2 mb-3 rounded bg-info-lighten-5" };

const {ref,reactive,onMounted,computed} = await importShared('vue');


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

// 智能输入框相关变量
const saleThresholdType = ref('price'); // 'price' 或 'percentage'

// 计算属性：根据类型设置相应的值
const saleThresholdValueComputed = computed({
  get() {
    if (saleThresholdType.value === 'price') {
      return editableConfig.sale_price_threshold;
    } else {
      return editableConfig.sale_profit_percentage;
    }
  },
  set(value) {
    if (saleThresholdType.value === 'price') {
      editableConfig.sale_price_threshold = value;
    } else {
      editableConfig.sale_profit_percentage = value;
    }
  }
});

// 保存从服务器获取的配置，用于重置
const serverFetchedConfig = reactive({
  enabled: false,
  notify: false,
  cron: '',
  farm_interval: 5,
  use_proxy: false,
  retry_count: 3,
  cookie: '',
  onlyonce: false,
  auto_purchase_enabled: false,
  purchase_price_threshold: 0,
  purchase_quantity_ratio: 0.5,
  auto_sale_enabled: false,
  sale_price_threshold: 0,
  sale_quantity_ratio: 1,
  sale_profit_percentage: 0,
  sale_threshold_type: 'price', // 新增：保存出售条件类型
  expiry_sale_enabled: false, // 新增：到期出售开关
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
  onlyonce: false,
  auto_purchase_enabled: false,
  purchase_price_threshold: 0,
  purchase_quantity_ratio: 0.5,
  auto_sale_enabled: false,
  sale_price_threshold: 0,
  sale_quantity_ratio: 1,
  sale_profit_percentage: 0,
  expiry_sale_enabled: false, // 新增：到期出售开关
});

// 更新编辑中的配置
const setEditableConfig = (sourceConfig) => {
  if (sourceConfig && typeof sourceConfig === 'object') {
    Object.keys(editableConfig).forEach(key => {
      if (sourceConfig.hasOwnProperty(key)) {
        editableConfig[key] = JSON.parse(JSON.stringify(sourceConfig[key]));
      }
    });
    
    // 智能判断出售条件类型
    if (sourceConfig.sale_profit_percentage && sourceConfig.sale_profit_percentage > 0) {
      saleThresholdType.value = 'percentage';
    } else if (sourceConfig.sale_price_threshold && sourceConfig.sale_price_threshold > 0) {
      saleThresholdType.value = 'price';
    } else {
      // 默认使用价格阈值
      saleThresholdType.value = 'price';
    }
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
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_progress_circular = _resolveComponent("v-progress-circular");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_VCronField = _resolveComponent("VCronField");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_form = _resolveComponent("v-form");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_v_card, {
      flat: "",
      class: "rounded border"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center px-3 py-2" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_icon, {
              icon: "mdi-cog",
              class: "mr-2",
              color: "primary",
              size: "small"
            }),
            _cache[22] || (_cache[22] = _createElementVNode("span", null, "象岛农场配置", -1)),
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              color: "info",
              onClick: _cache[0] || (_cache[0] = $event => (emit('switch'))),
              "prepend-icon": "mdi-view-dashboard",
              disabled: saving.value,
              variant: "text",
              size: "small",
              class: "toolbar-btn"
            }, {
              default: _withCtx(() => _cache[18] || (_cache[18] = [
                _createElementVNode("span", { class: "btn-text" }, "状态页", -1)
              ])),
              _: 1
            }, 8, ["disabled"]),
            _createVNode(_component_v_btn, {
              color: "secondary",
              variant: "text",
              onClick: resetConfigToFetched,
              disabled: !initialConfigLoaded.value || saving.value,
              "prepend-icon": "mdi-restore",
              size: "small",
              class: "toolbar-btn"
            }, {
              default: _withCtx(() => _cache[19] || (_cache[19] = [
                _createElementVNode("span", { class: "btn-text" }, "重置", -1)
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
              size: "small",
              class: "toolbar-btn"
            }, {
              default: _withCtx(() => _cache[20] || (_cache[20] = [
                _createElementVNode("span", { class: "btn-text" }, "保存配置", -1)
              ])),
              _: 1
            }, 8, ["disabled", "loading"]),
            _createVNode(_component_v_btn, {
              color: "grey",
              onClick: _cache[1] || (_cache[1] = $event => (emit('close'))),
              "prepend-icon": "mdi-close",
              disabled: saving.value,
              variant: "text",
              size: "small",
              class: "toolbar-btn"
            }, {
              default: _withCtx(() => _cache[21] || (_cache[21] = [
                _createElementVNode("span", { class: "btn-text" }, "关闭", -1)
              ])),
              _: 1
            }, 8, ["disabled"])
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
              "onUpdate:modelValue": _cache[17] || (_cache[17] = $event => ((isFormValid).value = $event)),
              onSubmit: _withModifiers(saveFullConfig, ["prevent"])
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card, {
                  flat: "",
                  class: "rounded mb-3 border config-card"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card_title, { class: "text-subtitle-2 d-flex align-center px-3 py-2" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-tune",
                          class: "mr-2",
                          color: "primary",
                          size: "small"
                        }),
                        _cache[23] || (_cache[23] = _createElementVNode("span", null, "基本设置", -1))
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
                                      _cache[24] || (_cache[24] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用插件"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "是否启用象岛农场插件")
                                      ], -1)),
                                      _createVNode(CustomSwitch, {
                                        modelValue: editableConfig.enabled,
                                        "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((editableConfig.enabled) = $event)),
                                        disabled: saving.value
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
                                      _cache[25] || (_cache[25] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用通知"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "完成后发送消息通知")
                                      ], -1)),
                                      _createVNode(CustomSwitch, {
                                        modelValue: editableConfig.notify,
                                        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((editableConfig.notify) = $event)),
                                        disabled: saving.value
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
                                      _cache[26] || (_cache[26] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "使用代理"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "是否使用系统代理访问")
                                      ], -1)),
                                      _createVNode(CustomSwitch, {
                                        modelValue: editableConfig.use_proxy,
                                        "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((editableConfig.use_proxy) = $event)),
                                        disabled: saving.value
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
                    _createVNode(_component_v_card_title, { class: "text-subtitle-2 d-flex align-center px-3 py-2" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-clock-time-five",
                          class: "mr-2",
                          color: "primary",
                          size: "small"
                        }),
                        _cache[27] || (_cache[27] = _createElementVNode("span", null, "执行设置", -1))
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
                                  "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((editableConfig.cookie) = $event)),
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
                                    _createElementVNode("div", _hoisted_11, [
                                      _createVNode(_component_v_btn, {
                                        icon: "",
                                        variant: "tonal",
                                        color: "secondary",
                                        onClick: fillWithSiteCookie,
                                        disabled: saving.value || loadingCookie.value,
                                        size: "small",
                                        class: "tooltip-btn"
                                      }, {
                                        default: _withCtx(() => [
                                          (!loadingCookie.value)
                                            ? (_openBlock(), _createBlock(_component_v_icon, {
                                                key: 0,
                                                color: "secondary",
                                                size: "small",
                                                class: "tooltip-icon"
                                              }, {
                                                default: _withCtx(() => _cache[28] || (_cache[28] = [
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
                                        _: 1
                                      }, 8, ["disabled"]),
                                      _cache[29] || (_cache[29] = _createElementVNode("div", { class: "custom-tooltip" }, [
                                        _createElementVNode("div", { class: "custom-tooltip-content" }, [
                                          _createElementVNode("span", { class: "tooltip-text" }, "使用已添加站点的Cookie")
                                        ])
                                      ], -1))
                                    ])
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
                                  "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((editableConfig.cron) = $event)),
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
                                  "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((editableConfig.farm_interval) = $event)),
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
                                  "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((editableConfig.retry_count) = $event)),
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
                _createVNode(_component_v_card, {
                  flat: "",
                  class: "rounded mb-3 border config-card"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card_title, { class: "text-subtitle-2 d-flex align-center px-3 py-2" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-cart",
                          class: "mr-2",
                          color: "primary",
                          size: "small"
                        }),
                        _cache[30] || (_cache[30] = _createElementVNode("span", null, "自动交易设置", -1))
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
                                _createElementVNode("div", _hoisted_12, [
                                  _createVNode(_component_v_icon, {
                                    icon: "mdi-cart-arrow-down",
                                    size: "small",
                                    color: editableConfig.auto_purchase_enabled ? 'success' : 'grey',
                                    class: "mr-3"
                                  }, null, 8, ["color"]),
                                  _createElementVNode("div", _hoisted_13, [
                                    _createElementVNode("div", _hoisted_14, [
                                      _cache[31] || (_cache[31] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用自动进货"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "当农场价格低于阈值时自动进货")
                                      ], -1)),
                                      _createVNode(CustomSwitch, {
                                        modelValue: editableConfig.auto_purchase_enabled,
                                        "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((editableConfig.auto_purchase_enabled) = $event)),
                                        disabled: saving.value
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
                                _createElementVNode("div", _hoisted_15, [
                                  _createVNode(_component_v_icon, {
                                    icon: "mdi-cart-arrow-up",
                                    size: "small",
                                    color: editableConfig.auto_sale_enabled ? 'success' : 'grey',
                                    class: "mr-3"
                                  }, null, 8, ["color"]),
                                  _createElementVNode("div", _hoisted_16, [
                                    _createElementVNode("div", _hoisted_17, [
                                      _cache[32] || (_cache[32] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用自动出售"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "当蔬菜店价格高于阈值时自动出售")
                                      ], -1)),
                                      _createVNode(CustomSwitch, {
                                        modelValue: editableConfig.auto_sale_enabled,
                                        "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((editableConfig.auto_sale_enabled) = $event)),
                                        disabled: saving.value
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
                                _createElementVNode("div", _hoisted_18, [
                                  _createVNode(_component_v_icon, {
                                    icon: "mdi-calendar-clock",
                                    size: "small",
                                    color: editableConfig.expiry_sale_enabled ? 'warning' : 'grey',
                                    class: "mr-3"
                                  }, null, 8, ["color"]),
                                  _createElementVNode("div", _hoisted_19, [
                                    _createElementVNode("div", _hoisted_20, [
                                      _cache[33] || (_cache[33] = _createElementVNode("div", null, [
                                        _createElementVNode("div", { class: "text-subtitle-2" }, "启用到期出售"),
                                        _createElementVNode("div", { class: "text-caption text-grey" }, "每周六14点前无论是否亏损将执行全部出售")
                                      ], -1)),
                                      _createVNode(CustomSwitch, {
                                        modelValue: editableConfig.expiry_sale_enabled,
                                        "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((editableConfig.expiry_sale_enabled) = $event)),
                                        disabled: saving.value
                                      }, null, 8, ["modelValue", "disabled"])
                                    ])
                                  ])
                                ])
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_row, null, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_col, {
                              cols: "12",
                              md: "6"
                            }, {
                              default: _withCtx(() => [
                                (editableConfig.auto_purchase_enabled)
                                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: editableConfig.purchase_price_threshold,
                                        "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => ((editableConfig.purchase_price_threshold) = $event)),
                                        modelModifiers: { number: true },
                                        label: "进货价格阈值",
                                        type: "number",
                                        variant: "outlined",
                                        min: 0,
                                        rules: [v => v === null || v === '' || (Number(v) >= 0) || '价格必须大于等于0'],
                                        hint: "当农场价格低于或等于此价格时自动进货（阀值为0时不执行）",
                                        "persistent-hint": "",
                                        "prepend-inner-icon": "mdi-currency-usd",
                                        disabled: saving.value,
                                        density: "compact",
                                        class: "text-caption mb-5"
                                      }, null, 8, ["modelValue", "rules", "disabled"]),
                                      _createVNode(_component_v_select, {
                                        modelValue: editableConfig.purchase_quantity_ratio,
                                        "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((editableConfig.purchase_quantity_ratio) = $event)),
                                        label: "进货数量比例",
                                        items: [
                        { title: '20%', value: 0.2 },
                        { title: '50%', value: 0.5 },
                        { title: '80%', value: 0.8 },
                        { title: '全部', value: 1 }
                      ],
                                        "item-title": "title",
                                        "item-value": "value",
                                        variant: "outlined",
                                        hint: "根据象草余额按比例进货",
                                        "persistent-hint": "",
                                        "prepend-inner-icon": "mdi-percent",
                                        disabled: saving.value,
                                        density: "compact",
                                        class: "text-caption"
                                      }, null, 8, ["modelValue", "disabled"])
                                    ], 64))
                                  : _createCommentVNode("", true)
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_v_col, {
                              cols: "12",
                              md: "6"
                            }, {
                              default: _withCtx(() => [
                                (editableConfig.auto_sale_enabled)
                                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                                      _createVNode(_component_v_row, null, {
                                        default: _withCtx(() => [
                                          _createVNode(_component_v_col, {
                                            cols: "12",
                                            md: "12",
                                            style: {"min-width":"0"}
                                          }, {
                                            default: _withCtx(() => [
                                              _createElementVNode("div", _hoisted_21, [
                                                _createVNode(_component_v_select, {
                                                  modelValue: saleThresholdType.value,
                                                  "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => ((saleThresholdType).value = $event)),
                                                  label: "出售条件类型",
                                                  items: [
                              { title: '价格阈值', value: 'price' },
                              { title: '盈利百分比', value: 'percentage' }
                            ],
                                                  "item-title": "title",
                                                  "item-value": "value",
                                                  variant: "outlined",
                                                  "persistent-hint": "",
                                                  "prepend-inner-icon": "mdi-tune",
                                                  disabled: saving.value,
                                                  density: "compact",
                                                  class: "text-caption",
                                                  style: {"flex":"1 1 0","min-width":"160px","max-width":"260px"}
                                                }, null, 8, ["modelValue", "disabled"]),
                                                _createVNode(_component_v_text_field, {
                                                  modelValue: saleThresholdValueComputed.value,
                                                  "onUpdate:modelValue": _cache[15] || (_cache[15] = $event => ((saleThresholdValueComputed).value = $event)),
                                                  modelModifiers: { number: true },
                                                  label: saleThresholdType.value === 'price' ? '出售价格阈值' : '盈利百分比阈值',
                                                  type: "number",
                                                  variant: "outlined",
                                                  min: 0,
                                                  max: saleThresholdType.value === 'percentage' ? 1000 : undefined,
                                                  rules: saleThresholdType.value === 'price' 
                              ? [v => v === null || v === '' || (Number(v) >= 0) || '价格必须大于等于0']
                              : [v => v === null || v === '' || (Number(v) >= 0 && Number(v) <= 1000) || '百分比必须在0-1000之间'],
                                                  "persistent-hint": "",
                                                  "prepend-inner-icon": saleThresholdType.value === 'price' ? 'mdi-currency-usd' : 'mdi-percent',
                                                  disabled: saving.value,
                                                  density: "compact",
                                                  class: "text-caption",
                                                  style: {"flex":"1 1 0","min-width":"160px","max-width":"260px"}
                                                }, null, 8, ["modelValue", "label", "max", "rules", "prepend-inner-icon", "disabled"])
                                              ]),
                                              _createElementVNode("div", _hoisted_22, [
                                                (saleThresholdType.value === 'price')
                                                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                                                      _createTextVNode(" 当蔬菜店价格高于或等于此价格时自动出售（阈值为0时不执行） ")
                                                    ], 64))
                                                  : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                                                      _createTextVNode(" 当盈利百分比达到或超过此值时自动出售（设为0时不执行） ")
                                                    ], 64))
                                              ])
                                            ]),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_select, {
                                        modelValue: editableConfig.sale_quantity_ratio,
                                        "onUpdate:modelValue": _cache[16] || (_cache[16] = $event => ((editableConfig.sale_quantity_ratio) = $event)),
                                        label: "出售数量比例",
                                        items: [
                        { title: '20%', value: 0.2 },
                        { title: '50%', value: 0.5 },
                        { title: '80%', value: 0.8 },
                        { title: '全部', value: 1 }
                      ],
                                        "item-title": "title",
                                        "item-value": "value",
                                        variant: "outlined",
                                        hint: "根据库存按比例出售",
                                        "persistent-hint": "",
                                        "prepend-inner-icon": "mdi-percent",
                                        disabled: saving.value,
                                        density: "compact",
                                        class: "text-caption"
                                      }, null, 8, ["modelValue", "disabled"])
                                    ], 64))
                                  : _createCommentVNode("", true)
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
                _createElementVNode("div", _hoisted_23, [
                  _createVNode(_component_v_icon, {
                    icon: "mdi-information",
                    color: "info",
                    class: "mr-2",
                    size: "small"
                  }),
                  _cache[34] || (_cache[34] = _createElementVNode("span", { class: "text-caption" }, " 此插件用于监听象岛农场相关信息，支持定时执行、代理访问、失败重试等功能。 获取象岛农场信息，建议根据实际情况调整。 ", -1))
                ])
              ]),
              _: 1
            }, 8, ["modelValue"])
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
const ConfigComponent = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-7998ca2e"]]);

export { ConfigComponent as default };
