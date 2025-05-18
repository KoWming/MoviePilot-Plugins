import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const Page_vue_vue_type_style_index_0_scoped_5bfbfe5d_lang = '';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,toDisplayString:_toDisplayString,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,Fragment:_Fragment,createElementBlock:_createElementBlock,mergeProps:_mergeProps,renderList:_renderList} = await importShared('vue');


const _hoisted_1 = { class: "plugin-page" };
const _hoisted_2 = { class: "text-subtitle-2" };
const _hoisted_3 = { class: "text-subtitle-2" };
const _hoisted_4 = { class: "text-subtitle-2" };
const _hoisted_5 = { class: "text-subtitle-2" };
const _hoisted_6 = { class: "text-subtitle-2" };
const _hoisted_7 = { class: "text-subtitle-2" };
const _hoisted_8 = ["title"];
const _hoisted_9 = { class: "text-caption text-grey" };
const _hoisted_10 = { class: "timeline-date" };
const _hoisted_11 = { class: "text-caption" };
const _hoisted_12 = { class: "text-body-2" };
const _hoisted_13 = { class: "text-body-2" };
const _hoisted_14 = { class: "text-body-2" };
const _hoisted_15 = { class: "text-subtitle-2" };
const _hoisted_16 = { class: "text-subtitle-2" };
const _hoisted_17 = { class: "text-subtitle-2" };
const _hoisted_18 = { class: "text-subtitle-2" };
const _hoisted_19 = { class: "text-subtitle-2" };
const _hoisted_20 = { class: "text-subtitle-2" };
const _hoisted_21 = { class: "text-subtitle-2" };
const _hoisted_22 = { class: "text-subtitle-2" };
const _hoisted_23 = { style: {"margin-bottom":"12px"} };
const _hoisted_24 = { style: {"margin-bottom":"12px"} };
const _hoisted_25 = { style: {"margin-bottom":"12px"} };
const _hoisted_26 = {
  key: 0,
  style: {"margin-bottom":"12px"}
};
const _hoisted_27 = { style: {"margin-bottom":"12px"} };
const _hoisted_28 = { style: {"margin-bottom":"12px"} };
const _hoisted_29 = { style: {"margin-bottom":"12px"} };
const _hoisted_30 = {
  key: 0,
  style: {"margin-bottom":"12px"}
};

const {ref,reactive,onMounted,computed} = await importShared('vue');



const _sfc_main = {
  __name: 'Page',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  }
},
  emits: ['close', 'switch'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

const loading = ref(false);
const error = ref(null);
const successMessage = ref(null);

// 状态数据
const status = reactive({
  enabled: false,
  next_run_time: null,
  farm_interval: 15,
  use_proxy: true,
  retry_count: 2,
  sign_dict: []
});

// 最新一条农场和蔬菜店信息
const latestFarmInfo = computed(() => {
  if (status.sign_dict && status.sign_dict.length > 0) {
    const firstRecord = status.sign_dict[0];
    if (firstRecord && firstRecord.farm_info) {
      return firstRecord.farm_info;
    }
  }
  return {};
});

// 购买相关
const purchaseAmount = ref('');
const purchaseDialog = ref(false);
const purchaseLoading = ref(false);
const purchaseError = ref('');
const purchaseSuccess = ref('');

// 出售相关
const saleDialog = ref(false);
const saleAmount = ref('');
const saleLoading = ref(false);
const saleError = ref('');
const saleSuccess = ref('');

// 获取插件ID
const getPluginId = () => {
  return "VicomoFarm";
};

// 获取时间线点的颜色
const getTimelineDotColor = (item, index) => {
  const colors = ['primary', 'secondary', 'success', 'info', 'warning', 'error'];
  // 使用索引确保每个时间线项的颜色是固定的
  return colors[index % colors.length];
};

// 刷新数据
async function refreshData() {
  error.value = null;
  loading.value = true;
  try {
    const pluginId = getPluginId();
    if (!pluginId) ;
    const data = await props.api.get(`plugin/${pluginId}/status`);
    if (data) {
      Object.assign(status, data);
      if (Array.isArray(data.sign_dict)) {
        status.sign_dict.splice(0, status.sign_dict.length, ...data.sign_dict);
      }
      successMessage.value = '数据已刷新';
    } else {
      throw new Error('获取状态数据失败');
    }
  } catch (err) {
    error.value = err.message || '刷新数据失败，请检查网络或API';
  } finally {
    loading.value = false;
    setTimeout(() => { error.value = null; successMessage.value = null; }, 3000);
  }
}

// 购买操作
async function handlePurchase() {
  purchaseError.value = '';
  purchaseSuccess.value = '';
  purchaseLoading.value = true;
  try {
    const pluginId = getPluginId();
    const num = Number(purchaseAmount.value);
    if (!num || num <= 0 || !Number.isInteger(num)) {
      purchaseError.value = '请输入有效的购买数量';
      purchaseLoading.value = false;
      return;
    }
    const url = `plugin/${pluginId}/purchase?buy_num=${num}`;
    const res = await props.api.post(url);
    if (res && res.success) {
      purchaseSuccess.value = res.msg || '购买成功';
      // 前端临时减少剩余配货量
      if (latestFarmInfo.value && latestFarmInfo.value.farm && typeof latestFarmInfo.value.farm.剩余配货量 !== 'undefined') {
        let remain = parseInt(String(latestFarmInfo.value.farm.剩余配货量).replace(/,/g, ''));
        if (!isNaN(remain)) {
          let newRemain = remain - num;
          if (newRemain < 0) newRemain = 0;
          latestFarmInfo.value.farm.剩余配货量 = newRemain;
        }
      }
      // 前端临时增加蔬菜店库存
      if (latestFarmInfo.value && latestFarmInfo.value.vegetable_shop && typeof latestFarmInfo.value.vegetable_shop.库存 !== 'undefined') {
        let stock = parseInt(String(latestFarmInfo.value.vegetable_shop.库存).replace(/,/g, ''));
        if (!isNaN(stock)) {
          let newStock = stock + num;
          if (newStock < 0) newStock = 0;
          latestFarmInfo.value.vegetable_shop.库存 = newStock;
        }
      }
      purchaseAmount.value = '';
      // 延迟1.5秒后自动关闭弹窗
      setTimeout(() => {
        purchaseDialog.value = false;
      }, 1500);
      // 不立即刷新数据，等用户手动刷新
    } else {
      purchaseError.value = (res && res.msg) || '购买失败';
    }
  } catch (e) {
    purchaseError.value = e.message || '购买失败';
  } finally {
    purchaseLoading.value = false;
    setTimeout(() => { purchaseError.value = ''; }, 3000);
  }
}

// 刷新任务
async function refreshTask() {
  error.value = null;
  loading.value = true;
  
  try {
    const pluginId = getPluginId();
    if (!pluginId) ;
    
    const res = await props.api.post(`plugin/${pluginId}/task`);
    console.log('[VicomoFarm] refreshTask API response:', res);
    
    if (res) {
      // 刷新数据
      await refreshData();
    } else {
      // 这里打印 res 以便排查
      console.error('[VicomoFarm] refreshTask: res 为空或无效', res);
      throw new Error('执行任务失败');
    }
  } catch (err) {
    // 这里打印 err 的详细内容
    console.error('执行任务失败:', err, err && err.response, err && err.stack);
    error.value = (err && err.message) || '执行任务失败，请检查网络或API';
  } finally {
    loading.value = false;
    setTimeout(() => { error.value = null; }, 3000);
  }
}

// 出售操作
async function handleSale() {
  saleError.value = '';
  saleSuccess.value = '';
  saleDialog.value = true;
  saleLoading.value = true;
  try {
    const pluginId = getPluginId();
    const num = Number(saleAmount.value);
    const maxNum = Number(latestFarmInfo.value.vegetable_shop.可卖数量);
    if (!num || num <= 0 || !Number.isInteger(num)) {
      saleError.value = '请输入有效的出售数量';
      saleLoading.value = false;
      return;
    }
    if (num > maxNum) {
      saleError.value = `最大可卖数量为${maxNum}`;
      saleLoading.value = false;
      return;
    }
    const url = `plugin/${pluginId}/sale?sale_num=${num}`;
    const res = await props.api.post(url);
    if (res && res.success) {
      saleSuccess.value = res.msg || '出售成功';
      // 前端临时减少蔬菜店库存
      if (latestFarmInfo.value && latestFarmInfo.value.vegetable_shop && typeof latestFarmInfo.value.vegetable_shop.库存 !== 'undefined') {
        let stock = parseInt(String(latestFarmInfo.value.vegetable_shop.库存).replace(/,/g, ''));
        if (!isNaN(stock)) {
          let newStock = stock - num;
          if (newStock < 0) newStock = 0;
          latestFarmInfo.value.vegetable_shop.库存 = newStock;
        }
      }
      saleAmount.value = '';
      // 延迟1.5秒后自动关闭弹窗
      setTimeout(() => {
        saleDialog.value = false;
      }, 1500);
      refreshData();
    } else {
      saleError.value = (res && res.msg) || '出售失败';
    }
  } catch (e) {
    saleError.value = e.message || '出售失败';
  } finally {
    saleLoading.value = false;
    setTimeout(() => { saleError.value = ''; saleSuccess.value = ''; }, 3000);
  }
}

// 计算最大可进货数量
function calculateMaxPurchase() {
  if (!latestFarmInfo.value.bonus || !latestFarmInfo.value.farm.价格) {
    return 0;
  }
  // 去除千分位逗号
  const bonus = parseFloat(String(latestFarmInfo.value.bonus).replace(/,/g, ''));
  const price = parseFloat(String(latestFarmInfo.value.farm.价格).replace(/,/g, ''));
  if (isNaN(bonus) || isNaN(price) || price === 0) {
    return 0;
  }
  return Math.floor(bonus / price);
}

// 计算最大可出售数量
function calculateMaxSale() {
  if (!latestFarmInfo.value.bonus || !latestFarmInfo.value.farm.价格) {
    return 0;
  }
  // 去除千分位逗号
  const bonus = parseFloat(String(latestFarmInfo.value.bonus).replace(/,/g, ''));
  const price = parseFloat(String(latestFarmInfo.value.farm.价格).replace(/,/g, ''));
  if (isNaN(bonus) || isNaN(price) || price === 0) {
    return 0;
  }
  return Math.floor(bonus / price);
}

onMounted(() => {
  refreshData();
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_list_item_title = _resolveComponent("v-list-item-title");
  const _component_v_list_item_subtitle = _resolveComponent("v-list-item-subtitle");
  const _component_v_list_item = _resolveComponent("v-list-item");
  const _component_v_list = _resolveComponent("v-list");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_tooltip = _resolveComponent("v-tooltip");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_timeline_item = _resolveComponent("v-timeline-item");
  const _component_v_timeline = _resolveComponent("v-timeline");
  const _component_v_sheet = _resolveComponent("v-sheet");
  const _component_v_divider = _resolveComponent("v-divider");
  const _component_v_card_actions = _resolveComponent("v-card-actions");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_dialog = _resolveComponent("v-dialog");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_v_card, {
      flat: "",
      class: "rounded border"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_icon, {
              icon: "mdi-farm",
              class: "mr-2",
              color: "primary",
              size: "small"
            }),
            _cache[13] || (_cache[13] = _createElementVNode("span", null, "象岛农场", -1)),
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              color: "primary",
              variant: "text",
              size: "small",
              "prepend-icon": "mdi-refresh",
              onClick: refreshData,
              loading: loading.value
            }, {
              default: _withCtx(() => _cache[12] || (_cache[12] = [
                _createTextVNode("刷新")
              ])),
              _: 1
            }, 8, ["loading"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
          default: _withCtx(() => [
            (successMessage.value)
              ? (_openBlock(), _createBlock(_component_v_alert, {
                  key: 0,
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
            (error.value)
              ? (_openBlock(), _createBlock(_component_v_alert, {
                  key: 1,
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
            _createVNode(_component_v_row, {
              align: "stretch",
              class: "mb-0",
              "no-gutters": ""
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "6",
                  style: {"padding":"8px"}
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, {
                      flat: "",
                      class: "rounded border status-card h-100"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: "mdi-information",
                              class: "mr-2",
                              color: "primary",
                              size: "small"
                            }),
                            _cache[14] || (_cache[14] = _createElementVNode("span", null, "当前状态", -1))
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list, {
                              density: "compact",
                              class: "pa-0"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_list_item, null, {
                                  prepend: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-power",
                                      color: status.enabled ? 'success' : 'grey',
                                      size: "small"
                                    }, null, 8, ["color"])
                                  ]),
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_list_item_title, { class: "text-subtitle-2" }, {
                                      default: _withCtx(() => _cache[15] || (_cache[15] = [
                                        _createTextVNode("插件状态")
                                      ])),
                                      _: 1
                                    }),
                                    _createVNode(_component_v_list_item_subtitle, null, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(status.enabled ? '已启用' : '已禁用'), 1)
                                      ]),
                                      _: 1
                                    })
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_list_item, null, {
                                  prepend: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-clock-time-five",
                                      color: "info",
                                      size: "small"
                                    })
                                  ]),
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_list_item_title, { class: "text-subtitle-2" }, {
                                      default: _withCtx(() => _cache[16] || (_cache[16] = [
                                        _createTextVNode("下次执行时间")
                                      ])),
                                      _: 1
                                    }),
                                    _createVNode(_component_v_list_item_subtitle, null, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(status.next_run_time || '未设置'), 1)
                                      ]),
                                      _: 1
                                    })
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_list_item, null, {
                                  prepend: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-proxy",
                                      color: status.use_proxy ? 'info' : 'grey',
                                      size: "small"
                                    }, null, 8, ["color"])
                                  ]),
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_list_item_title, { class: "text-subtitle-2" }, {
                                      default: _withCtx(() => _cache[17] || (_cache[17] = [
                                        _createTextVNode("代理状态")
                                      ])),
                                      _: 1
                                    }),
                                    _createVNode(_component_v_list_item_subtitle, null, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(status.use_proxy ? '已启用' : '已禁用'), 1)
                                      ]),
                                      _: 1
                                    })
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_list_item, null, {
                                  prepend: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-timer",
                                      color: "primary",
                                      size: "small"
                                    })
                                  ]),
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_list_item_title, { class: "text-subtitle-2" }, {
                                      default: _withCtx(() => _cache[18] || (_cache[18] = [
                                        _createTextVNode("重试间隔")
                                      ])),
                                      _: 1
                                    }),
                                    _createVNode(_component_v_list_item_subtitle, null, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(status.farm_interval ? `${status.farm_interval}秒` : '未设置'), 1)
                                      ]),
                                      _: 1
                                    })
                                  ]),
                                  _: 1
                                }),
                                _createVNode(_component_v_list_item, null, {
                                  prepend: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      icon: "mdi-refresh",
                                      color: "primary",
                                      size: "small"
                                    })
                                  ]),
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_list_item_title, { class: "text-subtitle-2" }, {
                                      default: _withCtx(() => _cache[19] || (_cache[19] = [
                                        _createTextVNode("重试次数")
                                      ])),
                                      _: 1
                                    }),
                                    _createVNode(_component_v_list_item_subtitle, null, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(status.retry_count || '未设置'), 1)
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
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "6",
                  style: {"padding":"8px"}
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, {
                      flat: "",
                      class: "border rounded info-card h-100",
                      style: {"height":"100%"}
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_title, { class: "text-caption px-3 py-2 bg-primary-lighten-5 d-flex align-center" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: "mdi-farm",
                              class: "mr-2",
                              color: "primary",
                              size: "small"
                            }),
                            _cache[21] || (_cache[21] = _createElementVNode("span", null, "农场信息", -1)),
                            _createVNode(_component_v_spacer),
                            _createVNode(_component_v_btn, {
                              color: "primary",
                              variant: "text",
                              size: "small",
                              "prepend-icon": "mdi-refresh",
                              onClick: refreshTask,
                              loading: loading.value
                            }, {
                              default: _withCtx(() => _cache[20] || (_cache[20] = [
                                _createTextVNode("刷新农场信息")
                              ])),
                              _: 1
                            }, 8, ["loading"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list, {
                              density: "compact",
                              class: "pa-0"
                            }, {
                              default: _withCtx(() => [
                                (latestFarmInfo.value && latestFarmInfo.value.farm)
                                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-label",
                                            color: "primary",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[22] || (_cache[22] = _createElementVNode("span", null, "名称：", -1)),
                                          _createElementVNode("span", _hoisted_2, _toDisplayString(latestFarmInfo.value.farm.名称 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-shape",
                                            color: "info",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[23] || (_cache[23] = _createElementVNode("span", null, "类型：", -1)),
                                          _createElementVNode("span", _hoisted_3, _toDisplayString(latestFarmInfo.value.farm.类型 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-information",
                                            color: "success",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[24] || (_cache[24] = _createElementVNode("span", null, "状态：", -1)),
                                          _createElementVNode("span", _hoisted_4, _toDisplayString(latestFarmInfo.value.farm.状态 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-currency-cny",
                                            color: "warning",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[25] || (_cache[25] = _createElementVNode("span", null, "价格：", -1)),
                                          _createElementVNode("span", _hoisted_5, _toDisplayString(latestFarmInfo.value.farm.价格 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-package-variant",
                                            color: "warning",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[27] || (_cache[27] = _createElementVNode("span", null, "剩余配货量：", -1)),
                                          _createElementVNode("span", _hoisted_6, _toDisplayString(latestFarmInfo.value.farm.剩余配货量 || '未知') + "kg", 1),
                                          (latestFarmInfo.value.farm.剩余配货量 && latestFarmInfo.value.farm.剩余配货量 !== '未知' && Number(latestFarmInfo.value.farm.剩余配货量) > 0)
                                            ? (_openBlock(), _createBlock(_component_v_btn, {
                                                key: 0,
                                                color: "primary",
                                                size: "x-small",
                                                class: "ml-2",
                                                onClick: _cache[0] || (_cache[0] = $event => (purchaseDialog.value = true))
                                              }, {
                                                default: _withCtx(() => _cache[26] || (_cache[26] = [
                                                  _createTextVNode("进货")
                                                ])),
                                                _: 1
                                              }))
                                            : _createCommentVNode("", true)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-note-text",
                                            color: "secondary",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[28] || (_cache[28] = _createElementVNode("span", null, "说明：", -1)),
                                          _createElementVNode("span", _hoisted_7, _toDisplayString(latestFarmInfo.value.farm.说明 || '无'), 1)
                                        ]),
                                        _: 1
                                      })
                                    ], 64))
                                  : (_openBlock(), _createBlock(_component_v_list_item, { key: 1 }, {
                                      default: _withCtx(() => [
                                        _cache[30] || (_cache[30] = _createElementVNode("span", { class: "text-subtitle-2" }, "暂无数据", -1)),
                                        _createVNode(_component_v_tooltip, { location: "top" }, {
                                          activator: _withCtx(({ props }) => [
                                            _createVNode(_component_v_icon, _mergeProps(props, {
                                              icon: "mdi-help-circle",
                                              color: "grey",
                                              size: "small",
                                              class: "ml-2"
                                            }), null, 16)
                                          ]),
                                          default: _withCtx(() => [
                                            _cache[29] || (_cache[29] = _createElementVNode("span", null, "数据加载中或暂无数据", -1))
                                          ]),
                                          _: 1
                                        })
                                      ]),
                                      _: 1
                                    }))
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
                })
              ]),
              _: 1
            }),
            _createVNode(_component_v_row, {
              class: "mt-1",
              "no-gutters": ""
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "6",
                  style: {"padding":"8px"}
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, {
                      flat: "",
                      class: "rounded border status-card h-100"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: "mdi-history",
                              class: "mr-2",
                              color: "primary",
                              size: "small"
                            }),
                            _cache[31] || (_cache[31] = _createElementVNode("span", null, "历史记录", -1))
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_sheet, {
                              class: "history-container",
                              "max-height": "400"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_timeline, {
                                  density: "compact",
                                  align: "start",
                                  class: "pa-0"
                                }, {
                                  default: _withCtx(() => [
                                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(status.sign_dict, (item, index) => {
                                      return (_openBlock(), _createBlock(_component_v_timeline_item, {
                                        key: index,
                                        "dot-color": getTimelineDotColor(item, index),
                                        size: "x-small",
                                        class: "mb-2 timeline-item"
                                      }, {
                                        dot: _withCtx(() => [
                                          _createElementVNode("div", {
                                            class: "timeline-dot",
                                            title: item.date
                                          }, null, 8, _hoisted_8)
                                        ]),
                                        opposite: _withCtx(() => [
                                          _createElementVNode("div", _hoisted_9, _toDisplayString(item.date), 1)
                                        ]),
                                        default: _withCtx(() => [
                                          _createElementVNode("div", _hoisted_10, _toDisplayString(item.date), 1),
                                          _createElementVNode("div", _hoisted_11, [
                                            _cache[32] || (_cache[32] = _createElementVNode("div", { class: "text-subtitle-2 mb-1" }, "象草余额", -1)),
                                            _createElementVNode("div", _hoisted_12, _toDisplayString(item.farm_info.bonus || '未知'), 1),
                                            _cache[33] || (_cache[33] = _createElementVNode("div", { class: "text-subtitle-2 mt-2 mb-1" }, "农场信息", -1)),
                                            _createElementVNode("div", _hoisted_13, [
                                              _createElementVNode("div", null, "名称：" + _toDisplayString(item.farm_info.farm.名称 || '未知'), 1),
                                              _createElementVNode("div", null, "类型：" + _toDisplayString(item.farm_info.farm.类型 || '未知'), 1),
                                              _createElementVNode("div", null, "状态：" + _toDisplayString(item.farm_info.farm.状态 || '未知'), 1),
                                              _createElementVNode("div", null, "剩余配货量：" + _toDisplayString(item.farm_info.farm.剩余配货量 || '未知') + "kg", 1),
                                              _createElementVNode("div", null, "说明：" + _toDisplayString(item.farm_info.farm.说明 || '无'), 1)
                                            ]),
                                            _cache[34] || (_cache[34] = _createElementVNode("div", { class: "text-subtitle-2 mt-2 mb-1" }, "蔬菜店信息", -1)),
                                            _createElementVNode("div", _hoisted_14, [
                                              _createElementVNode("div", null, "名称：" + _toDisplayString(item.farm_info.vegetable_shop.名称 || '未知'), 1),
                                              _createElementVNode("div", null, "市场单价：" + _toDisplayString(item.farm_info.vegetable_shop.市场单价 || '未知'), 1),
                                              _createElementVNode("div", null, "库存：" + _toDisplayString(item.farm_info.vegetable_shop.库存 || '未知'), 1),
                                              _createElementVNode("div", null, "成本：" + _toDisplayString(item.farm_info.vegetable_shop.成本 || '未知'), 1),
                                              _createElementVNode("div", null, "开店累计盈利：" + _toDisplayString(item.farm_info.vegetable_shop.开店累计盈利 || '未知'), 1),
                                              _createElementVNode("div", null, "盈利目标：" + _toDisplayString(item.farm_info.vegetable_shop.盈利目标 || '未知'), 1),
                                              _createElementVNode("div", null, "可卖数量：" + _toDisplayString(item.farm_info.vegetable_shop.可卖数量 || '未知'), 1),
                                              _createElementVNode("div", null, "说明：" + _toDisplayString(item.farm_info.vegetable_shop.说明 || '无'), 1)
                                            ])
                                          ])
                                        ]),
                                        _: 2
                                      }, 1032, ["dot-color"]))
                                    }), 128))
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
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_col, {
                  cols: "12",
                  md: "6",
                  style: {"padding":"8px"}
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, {
                      flat: "",
                      class: "border rounded info-card h-100",
                      style: {"height":"100%","min-height":"300px"}
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_title, { class: "text-caption px-3 py-2 bg-primary-lighten-5 d-flex align-center" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              icon: "mdi-storefront",
                              class: "mr-2",
                              color: "primary",
                              size: "small"
                            }),
                            _cache[35] || (_cache[35] = _createElementVNode("span", null, "蔬菜店信息", -1))
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, { class: "px-3 py-2" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list, {
                              density: "compact",
                              class: "pa-0"
                            }, {
                              default: _withCtx(() => [
                                (latestFarmInfo.value && latestFarmInfo.value.vegetable_shop)
                                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-label",
                                            color: "primary",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[36] || (_cache[36] = _createElementVNode("span", null, "名称：", -1)),
                                          _createElementVNode("span", _hoisted_15, _toDisplayString(latestFarmInfo.value.vegetable_shop.名称 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-currency-cny",
                                            color: "info",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[37] || (_cache[37] = _createElementVNode("span", null, "市场单价：", -1)),
                                          _createElementVNode("span", _hoisted_16, _toDisplayString(latestFarmInfo.value.vegetable_shop.市场单价 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-warehouse",
                                            color: "success",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[38] || (_cache[38] = _createElementVNode("span", null, "库存：", -1)),
                                          _createElementVNode("span", _hoisted_17, _toDisplayString(latestFarmInfo.value.vegetable_shop.库存 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-cash",
                                            color: "warning",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[39] || (_cache[39] = _createElementVNode("span", null, "成本：", -1)),
                                          _createElementVNode("span", _hoisted_18, _toDisplayString(latestFarmInfo.value.vegetable_shop.成本 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-chart-line",
                                            color: "secondary",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[40] || (_cache[40] = _createElementVNode("span", null, "开店累计盈利：", -1)),
                                          _createElementVNode("span", _hoisted_19, _toDisplayString(latestFarmInfo.value.vegetable_shop.开店累计盈利 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-target",
                                            color: "error",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[41] || (_cache[41] = _createElementVNode("span", null, "盈利目标：", -1)),
                                          _createElementVNode("span", _hoisted_20, _toDisplayString(latestFarmInfo.value.vegetable_shop.盈利目标 || '未知'), 1)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-numeric",
                                            color: "primary",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[43] || (_cache[43] = _createElementVNode("span", null, "可卖数量：", -1)),
                                          _createElementVNode("span", _hoisted_21, _toDisplayString(latestFarmInfo.value.vegetable_shop.可卖数量 || '未知'), 1),
                                          (latestFarmInfo.value.vegetable_shop.可卖数量 && latestFarmInfo.value.vegetable_shop.可卖数量 !== '未知' && Number(latestFarmInfo.value.vegetable_shop.可卖数量) > 0)
                                            ? (_openBlock(), _createBlock(_component_v_btn, {
                                                key: 0,
                                                color: "success",
                                                size: "x-small",
                                                class: "ml-2",
                                                onClick: _cache[1] || (_cache[1] = $event => (saleDialog.value = true))
                                              }, {
                                                default: _withCtx(() => _cache[42] || (_cache[42] = [
                                                  _createTextVNode("出售")
                                                ])),
                                                _: 1
                                              }))
                                            : _createCommentVNode("", true)
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_list_item, { class: "d-flex align-center" }, {
                                        prepend: _withCtx(() => [
                                          _createVNode(_component_v_icon, {
                                            icon: "mdi-note-text",
                                            color: "grey",
                                            size: "small"
                                          })
                                        ]),
                                        default: _withCtx(() => [
                                          _cache[44] || (_cache[44] = _createElementVNode("span", null, "说明：", -1)),
                                          _createElementVNode("span", _hoisted_22, _toDisplayString(latestFarmInfo.value.vegetable_shop.说明 || '无'), 1)
                                        ]),
                                        _: 1
                                      })
                                    ], 64))
                                  : (_openBlock(), _createBlock(_component_v_list_item, { key: 1 }, {
                                      default: _withCtx(() => [
                                        _cache[46] || (_cache[46] = _createElementVNode("span", { class: "text-subtitle-2" }, "暂无数据", -1)),
                                        _createVNode(_component_v_tooltip, { location: "top" }, {
                                          activator: _withCtx(({ props }) => [
                                            _createVNode(_component_v_icon, _mergeProps(props, {
                                              icon: "mdi-help-circle",
                                              color: "grey",
                                              size: "small",
                                              class: "ml-2"
                                            }), null, 16)
                                          ]),
                                          default: _withCtx(() => [
                                            _cache[45] || (_cache[45] = _createElementVNode("span", null, "数据加载中或暂无数据", -1))
                                          ]),
                                          _: 1
                                        })
                                      ]),
                                      _: 1
                                    }))
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
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_divider),
        _createVNode(_component_v_card_actions, { class: "px-2 py-1" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_btn, {
              color: "info",
              onClick: _cache[2] || (_cache[2] = $event => (emit('switch'))),
              "prepend-icon": "mdi-cog",
              disabled: loading.value,
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => _cache[47] || (_cache[47] = [
                _createTextVNode("配置页")
              ])),
              _: 1
            }, 8, ["disabled"]),
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              color: "grey",
              onClick: _cache[3] || (_cache[3] = $event => (emit('close'))),
              "prepend-icon": "mdi-close",
              disabled: loading.value,
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => _cache[48] || (_cache[48] = [
                _createTextVNode("关闭")
              ])),
              _: 1
            }, 8, ["disabled"])
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    _createVNode(_component_v_dialog, {
      modelValue: purchaseDialog.value,
      "onUpdate:modelValue": [
        _cache[6] || (_cache[6] = $event => ((purchaseDialog).value = $event)),
        _cache[7] || (_cache[7] = val => { if (!val) { purchaseSuccess.value.value = ''; purchaseError.value.value = ''; purchaseAmount.value.value = ''; } })
      ],
      "max-width": "340"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, { class: "text-subtitle-2" }, {
              default: _withCtx(() => _cache[49] || (_cache[49] = [
                _createTextVNode("确认进货")
              ])),
              _: 1
            }),
            _createVNode(_component_v_card_text, null, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_23, [
                  _cache[50] || (_cache[50] = _createTextVNode(" 当前剩余配货量： ")),
                  _createElementVNode("b", null, _toDisplayString(latestFarmInfo.value.farm.剩余配货量 || '未知'), 1),
                  _cache[51] || (_cache[51] = _createTextVNode(" kg "))
                ]),
                _createElementVNode("div", _hoisted_24, [
                  _cache[52] || (_cache[52] = _createTextVNode(" 当前象草余额： ")),
                  _createElementVNode("b", null, _toDisplayString(latestFarmInfo.value.bonus || '未知'), 1)
                ]),
                _createElementVNode("div", _hoisted_25, [
                  _cache[53] || (_cache[53] = _createTextVNode(" 商品单价： ")),
                  _createElementVNode("b", null, _toDisplayString(latestFarmInfo.value.farm.价格 || '未知'), 1)
                ]),
                (latestFarmInfo.value.bonus && latestFarmInfo.value.farm.价格)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_26, [
                      _cache[54] || (_cache[54] = _createTextVNode(" 目前最多可进货： ")),
                      _createElementVNode("b", null, _toDisplayString(calculateMaxPurchase()), 1),
                      _cache[55] || (_cache[55] = _createTextVNode(" kg "))
                    ]))
                  : _createCommentVNode("", true),
                _createVNode(_component_v_text_field, {
                  modelValue: purchaseAmount.value,
                  "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((purchaseAmount).value = $event)),
                  label: "进货数量（kg）",
                  placeholder: "请输入进货数量",
                  type: "number",
                  rules: [
              v => !!v || '请输入进货数量',
              v => Number(v) > 0 || '数量需大于0',
              v => Number(v) <= Number(latestFarmInfo.value.farm.剩余配货量) || '不能超过剩余配货量',
              v => Number(v) <= calculateMaxPurchase() || '不能超过可进货数量'
            ],
                  min: "1",
                  max: Math.min(Number(latestFarmInfo.value.farm.剩余配货量), calculateMaxPurchase()),
                  required: "",
                  "hide-details": "auto",
                  style: {"margin-bottom":"0"}
                }, null, 8, ["modelValue", "rules", "max"]),
                (purchaseError.value)
                  ? (_openBlock(), _createBlock(_component_v_alert, {
                      key: 1,
                      type: "error",
                      class: "mt-2",
                      density: "compact"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(purchaseError.value), 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode("", true),
                (purchaseSuccess.value)
                  ? (_openBlock(), _createBlock(_component_v_alert, {
                      key: 2,
                      type: "success",
                      class: "mt-2",
                      density: "compact"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(purchaseSuccess.value), 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode("", true)
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_actions, { class: "justify-end" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  loading: purchaseLoading.value,
                  onClick: handlePurchase,
                  class: "mr-2"
                }, {
                  default: _withCtx(() => _cache[56] || (_cache[56] = [
                    _createTextVNode("确定进货")
                  ])),
                  _: 1
                }, 8, ["loading"]),
                _createVNode(_component_v_btn, {
                  color: "grey",
                  text: "",
                  onClick: _cache[5] || (_cache[5] = $event => (purchaseDialog.value = false))
                }, {
                  default: _withCtx(() => _cache[57] || (_cache[57] = [
                    _createTextVNode("取消")
                  ])),
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
    }, 8, ["modelValue"]),
    _createVNode(_component_v_dialog, {
      modelValue: saleDialog.value,
      "onUpdate:modelValue": [
        _cache[10] || (_cache[10] = $event => ((saleDialog).value = $event)),
        _cache[11] || (_cache[11] = val => { if (!val) { saleSuccess.value.value = ''; saleError.value.value = ''; saleAmount.value.value = ''; } })
      ],
      "max-width": "340"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, { class: "text-subtitle-2" }, {
              default: _withCtx(() => _cache[58] || (_cache[58] = [
                _createTextVNode("确认出售")
              ])),
              _: 1
            }),
            _createVNode(_component_v_card_text, null, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_27, [
                  _cache[59] || (_cache[59] = _createTextVNode(" 当前剩余配货量： ")),
                  _createElementVNode("b", null, _toDisplayString(latestFarmInfo.value.farm.剩余配货量 || '未知'), 1),
                  _cache[60] || (_cache[60] = _createTextVNode(" kg "))
                ]),
                _createElementVNode("div", _hoisted_28, [
                  _cache[61] || (_cache[61] = _createTextVNode(" 当前象草余额： ")),
                  _createElementVNode("b", null, _toDisplayString(latestFarmInfo.value.bonus || '未知'), 1)
                ]),
                _createElementVNode("div", _hoisted_29, [
                  _cache[62] || (_cache[62] = _createTextVNode(" 商品单价： ")),
                  _createElementVNode("b", null, _toDisplayString(latestFarmInfo.value.farm.价格 || '未知'), 1)
                ]),
                (latestFarmInfo.value.bonus && latestFarmInfo.value.farm.价格)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_30, [
                      _cache[63] || (_cache[63] = _createTextVNode(" 目前最多可出售： ")),
                      _createElementVNode("b", null, _toDisplayString(calculateMaxSale()), 1),
                      _cache[64] || (_cache[64] = _createTextVNode(" kg "))
                    ]))
                  : _createCommentVNode("", true),
                _createVNode(_component_v_text_field, {
                  modelValue: saleAmount.value,
                  "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((saleAmount).value = $event)),
                  label: "出售数量（kg）",
                  placeholder: "请输入出售数量",
                  type: "number",
                  rules: [
              v => !!v || '请输入出售数量',
              v => Number(v) > 0 || '数量需大于0',
              v => Number(v) <= Number(latestFarmInfo.value.farm.剩余配货量) || '不能超过剩余配货量',
              v => Number(v) <= calculateMaxSale() || '不能超过可出售数量'
            ],
                  min: "1",
                  max: Math.min(Number(latestFarmInfo.value.farm.剩余配货量), calculateMaxSale()),
                  required: "",
                  "hide-details": "auto",
                  style: {"margin-bottom":"0"}
                }, null, 8, ["modelValue", "rules", "max"]),
                (saleError.value)
                  ? (_openBlock(), _createBlock(_component_v_alert, {
                      key: 1,
                      type: "error",
                      class: "mt-2",
                      density: "compact"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(saleError.value), 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode("", true),
                (saleSuccess.value)
                  ? (_openBlock(), _createBlock(_component_v_alert, {
                      key: 2,
                      type: "success",
                      class: "mt-2",
                      density: "compact"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(saleSuccess.value), 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode("", true)
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_actions, { class: "justify-end" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  loading: saleLoading.value,
                  onClick: handleSale,
                  class: "mr-2"
                }, {
                  default: _withCtx(() => _cache[65] || (_cache[65] = [
                    _createTextVNode("确定出售")
                  ])),
                  _: 1
                }, 8, ["loading"]),
                _createVNode(_component_v_btn, {
                  color: "grey",
                  text: "",
                  onClick: _cache[9] || (_cache[9] = $event => (saleDialog.value = false))
                }, {
                  default: _withCtx(() => _cache[66] || (_cache[66] = [
                    _createTextVNode("取消")
                  ])),
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
    }, 8, ["modelValue"])
  ]))
}
}

};
const PageComponent = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-5bfbfe5d"]]);

export { PageComponent as default };
