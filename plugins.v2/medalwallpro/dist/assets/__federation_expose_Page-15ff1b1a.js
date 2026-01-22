import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {createElementVNode:_createElementVNode,openBlock:_openBlock,createElementBlock:_createElementBlock,resolveComponent:_resolveComponent,createVNode:_createVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,toDisplayString:_toDisplayString,createBlock:_createBlock,createCommentVNode:_createCommentVNode,Transition:_Transition,renderList:_renderList,Fragment:_Fragment,withModifiers:_withModifiers,normalizeClass:_normalizeClass,normalizeStyle:_normalizeStyle,createStaticVNode:_createStaticVNode} = await importShared('vue');

const _hoisted_1 = {
  class: "plugin-page",
  id: "medalwall-pro-page"
};
const _hoisted_2 = {
  style: { "position": "absolute", "width": "0", "height": "0", "pointer-events": "none" },
  xmlns: "http://www.w3.org/2000/svg"
};
const _hoisted_3 = { style: { "position": "absolute", "top": "0", "left": "0", "right": "0", "z-index": "50", "padding": "0 10px 10px 10px" } };
const _hoisted_4 = { class: "px-3 mb-3" };
const _hoisted_5 = {
  class: "text-h6 font-weight-bold",
  style: { "line-height": "1.2" }
};
const _hoisted_6 = {
  class: "text-h6 font-weight-bold",
  style: { "line-height": "1.2" }
};
const _hoisted_7 = {
  class: "text-h6 font-weight-bold",
  style: { "line-height": "1.2" }
};
const _hoisted_8 = {
  class: "text-h6 font-weight-bold",
  style: { "line-height": "1.2" }
};
const _hoisted_9 = {
  key: 0,
  class: "d-flex justify-center align-center py-10"
};
const _hoisted_10 = {
  key: 2,
  class: "pb-10"
};
const _hoisted_11 = { class: "d-flex align-center justify-space-between px-4 mb-2 cursor-pointer" };
const _hoisted_12 = ["onClick"];
const _hoisted_13 = { class: "text-h6 font-weight-bold mr-1" };
const _hoisted_14 = { class: "d-flex align-center text-caption text-grey" };
const _hoisted_15 = { class: "mr-2" };
const _hoisted_16 = { class: "mr-2" };
const _hoisted_17 = {
  key: 0,
  class: "medal-corner-ribbon"
};
const _hoisted_18 = ["onClick"];
const _hoisted_19 = { class: "d-flex align-center justify-center fill-height bg-transparent" };
const _hoisted_20 = ["onClick"];
const _hoisted_21 = { class: "text-truncate text-caption text-center px-1 font-weight-bold text-grey-darken-1" };
const _hoisted_22 = {
  key: 0,
  class: "px-2 pt-4 pb-2 bg-grey-lighten-5 rounded-lg mt-2 mx-2"
};
const _hoisted_23 = {
  class: "d-flex flex-column justify-center flex-grow-1 overflow-hidden",
  style: { "min-width": "0" }
};
const _hoisted_24 = { class: "d-flex align-center justify-space-between mb-1" };
const _hoisted_25 = { class: "d-flex align-center overflow-hidden flex-grow-1 mr-2" };
const _hoisted_26 = ["title"];
const _hoisted_27 = { class: "d-flex flex-shrink-0 align-center" };
const _hoisted_28 = { class: "d-flex align-center mb-1" };
const _hoisted_29 = { class: "text-primary font-weight-bold text-caption" };
const _hoisted_30 = { style: { "font-size": "0.65rem" } };
const _hoisted_31 = ["title"];
const _hoisted_32 = {
  class: "text-caption text-grey-darken-1 d-flex flex-column mt-1",
  style: { "font-size": "0.7rem !important", "line-height": "1.4" }
};
const _hoisted_33 = {
  key: 0,
  class: "d-flex align-center"
};
const _hoisted_34 = {
  key: 1,
  class: "d-flex align-center"
};
const _hoisted_35 = {
  key: 2,
  class: "d-flex align-center"
};
const _hoisted_36 = {
  key: 3,
  class: "d-flex align-center"
};
const _hoisted_37 = {
  key: 4,
  class: "d-flex align-center"
};
const _hoisted_38 = {
  key: 5,
  class: "mt-1"
};
const {ref,onMounted,computed} = await importShared('vue');

const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Page",
  props: {
    api: {
      type: Object,
      default: () => {
      }
    }
  },
  emits: ["action", "switch", "close"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const medals = ref([]);
    const loading = ref(false);
    const refreshing = ref(false);
    const clearingCache = ref(false);
    const successMessage = ref("");
    const errorMessage = ref("");
    const totalMedals = computed(() => medals.value.length);
    const siteCount = computed(() => {
      const sites = new Set(medals.value.map((m) => m.site));
      return sites.size;
    });
    const ownedMedals = computed(() => {
      return medals.value.filter((m) => (m.purchase_status || "").trim() === "已拥有").length;
    });
    const availableMedals = computed(() => {
      return medals.value.filter((m) => {
        const status = (m.purchase_status || "").trim();
        if (status === "购买" || status === "赠送") {
          return checkTimeValidity(m.saleBeginTime, m.saleEndTime);
        }
        return false;
      }).length;
    });
    const refreshingSites = ref({});
    const config = ref(null);
    const allSites = ref([]);
    const expandedSite = ref(null);
    const activeTab = ref(null);
    onMounted(async () => {
      await Promise.all([fetchMedals(), fetchConfig(), fetchSites()]);
    });
    function checkTimeValidity(startTime, endTime) {
      if (!startTime || !endTime)
        return false;
      if (startTime.includes("不限") || endTime.includes("不限"))
        return true;
      if (startTime.includes("长期") || endTime.includes("长期"))
        return true;
      const start = startTime.split("~")[0].trim();
      const end = endTime.split("~")[0].trim();
      const now = /* @__PURE__ */ new Date();
      const startDate = new Date(start);
      const endDate = new Date(end);
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
        return false;
      }
      return now >= startDate && now <= endDate;
    }
    async function fetchMedals() {
      loading.value = true;
      try {
        const data = await props.api.get("plugin/MedalWallPro/medals");
        if (data) {
          medals.value = data;
          if (data.length === 0) {
          }
        }
      } catch (e) {
        console.error("Failed to fetch medals", e);
        showNotification("获取勋章数据失败", "error");
      } finally {
        loading.value = false;
      }
    }
    async function fetchConfig() {
      try {
        config.value = await props.api.get("plugin/MedalWallPro/config");
      } catch (e) {
        console.error("Failed to fetch config", e);
      }
    }
    async function fetchSites() {
      try {
        allSites.value = await props.api.get("plugin/MedalWallPro/sites");
      } catch (e) {
        console.error("Failed to fetch sites", e);
      }
    }
    function getSiteIdByName(siteName) {
      const site = allSites.value.find((s) => s.title === siteName);
      return site ? site.value : null;
    }
    async function runTask() {
      refreshing.value = true;
      try {
        const res = await props.api.post("plugin/MedalWallPro/run");
        if (res && res.success) {
          showNotification("刷新请求已发送,请稍候...", "success");
          setTimeout(fetchMedals, 3e3);
        } else {
          showNotification(res?.message || "刷新失败", "error");
        }
      } catch (e) {
        console.error("Task run failed", e);
        showNotification("刷新失败: " + (e.message || "未知错误"), "error");
      } finally {
        refreshing.value = false;
      }
    }
    async function refreshSingleSite(siteName, siteId) {
      refreshingSites.value[siteName] = true;
      try {
        const res = await props.api.post("plugin/MedalWallPro/refresh_site", { site_id: siteId });
        if (res && res.success) {
          showNotification(`${siteName} 刷新成功`, "success");
          await fetchMedals();
        } else {
          throw new Error(res?.message || "刷新失败");
        }
      } catch (e) {
        console.error("Single site refresh failed", e);
        showNotification(`${siteName} 刷新失败: ${e.message || "未知错误"}`, "error");
      } finally {
        refreshingSites.value[siteName] = false;
      }
    }
    async function clearCache() {
      clearingCache.value = true;
      try {
        const res = await props.api.post("plugin/MedalWallPro/clear_cache");
        if (res && res.success) {
          showNotification("缓存已清理", "success");
          await fetchMedals();
        } else {
          showNotification(res?.message || "清理缓存失败", "error");
        }
      } catch (e) {
        console.error("Clear cache failed", e);
        showNotification("清理缓存失败: " + (e.message || "未知错误"), "error");
      } finally {
        clearingCache.value = false;
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
    function notifySwitch() {
      emit("switch", "config");
    }
    function notifyClose() {
      emit("close");
    }
    const groupedMedals = computed(() => {
      const groups = {};
      const enabledSiteNames = /* @__PURE__ */ new Set();
      if (config.value && config.value.chat_sites) {
        config.value.chat_sites.forEach((siteId) => {
          const site = allSites.value.find((s) => s.value === siteId);
          if (site) {
            enabledSiteNames.add(site.title);
          }
        });
      } else if (allSites.value.length > 0) ;
      medals.value.forEach((medal) => {
        if (config.value && config.value.chat_sites && !enabledSiteNames.has(medal.site)) {
          return;
        }
        if (!groups[medal.site]) {
          groups[medal.site] = [];
        }
        groups[medal.site].push(medal);
      });
      if (config.value && config.value.chat_sites) {
        config.value.chat_sites.forEach((siteId) => {
          const site = allSites.value.find((s) => s.value === siteId);
          const siteName = site ? site.title : siteId;
          if (!groups[siteName]) {
            groups[siteName] = [];
          }
        });
      }
      return Object.keys(groups).map((site) => {
        const siteMedals = groups[site];
        const ownedCount = siteMedals.filter((m) => isOwned(m)).length;
        const totalCount = siteMedals.length;
        const progress = totalCount > 0 ? Math.round(ownedCount / totalCount * 100) : 0;
        siteMedals.sort((a, b) => {
          const ownedA = isOwned(a);
          const ownedB = isOwned(b);
          if (ownedA && !ownedB)
            return -1;
          if (!ownedB && ownedA)
            return 1;
          if (ownedA === ownedB) {
            const statusA = a.purchase_status || "";
            const statusB = b.purchase_status || "";
            const buyA = statusA.includes("购买") || statusA.includes("赠送");
            const buyB = statusB.includes("购买") || statusB.includes("赠送");
            if (buyA && !buyB)
              return -1;
            if (!buyA && buyB)
              return 1;
          }
          return 0;
        });
        return {
          site,
          medals: siteMedals,
          ownedCount,
          totalCount,
          progress
        };
      }).sort((a, b) => b.ownedCount - a.ownedCount);
    });
    function isOwned(medal) {
      const status = (medal.purchase_status || "").trim();
      return status === "已拥有";
    }
    const toggleDetails = (siteName) => {
      if (expandedSite.value === siteName) {
        expandedSite.value = null;
        activeTab.value = null;
      } else {
        expandedSite.value = siteName;
        const site = groupedMedals.value.find((s) => s.site === siteName);
        if (site && hasGroups(site.medals)) {
          const groups = getGroupNames(site.medals);
          if (groups.length > 0) {
            activeTab.value = groups[0];
          }
        } else {
          activeTab.value = null;
        }
      }
    };
    const hasGroups = (medals2) => {
      return medals2.some((medal) => !!medal.group);
    };
    const getGroupNames = (medals2) => {
      const groups = /* @__PURE__ */ new Set();
      medals2.forEach((medal) => {
        if (medal.group) {
          groups.add(medal.group);
        }
      });
      return Array.from(groups);
    };
    const getDisplayMedals = (medals2) => {
      if (!hasGroups(medals2) || !activeTab.value) {
        return medals2;
      }
      return medals2.filter((medal) => medal.group === activeTab.value);
    };
    function getCurrency(medal) {
      return medal.currency || "魔力";
    }
    function getProxiedImageUrl(imageUrl) {
      return imageUrl || "";
    }
    function formatPrice(price) {
      if (!price)
        return "0";
      return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
    function getMedalSize(medal) {
      const desc = medal.description || "";
      const name = medal.name || "";
      const site = medal.site || "";
      const isOurBits = site.toLowerCase().includes("ourbits") || site.includes("我堡");
      if (isOurBits) {
        if (desc.includes("大徽章") || desc.includes("大") || name.includes("（大）")) {
          return { stack: 100, detail: 90 };
        } else if (desc.includes("小徽章") || desc.includes("小") || name.includes("（小）")) {
          return { stack: 60, detail: 50 };
        }
      }
      return { stack: 80, detail: 70 };
    }
    function needsCircleMask(medal) {
      const site = medal.site || "";
      const name = medal.name || "";
      return site.toLowerCase().includes("longpt") && name.toUpperCase() === "MP";
    }
    function needsRemoveBlackBg(medal) {
      const site = medal.site || "";
      return site.includes("藏宝阁") || site.toLowerCase().includes("cangbaoge");
    }
    function getStackItemStyle() {
      return {
        border: "1px solid rgba(0,0,0,0.05)",
        boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
        width: "110px",
        // 固定宽度
        height: "140px"
        // 固定高度
      };
    }
    function getCardStyle() {
      return {
        // 还原旧版样式：移除自定义背景，使用CSS类定义的背景色
        // Revert to old style: Remove custom background, use CSS class
        border: "thin solid rgba(255, 255, 255, 0.1)",
        transition: "transform 0.2s, box-shadow 0.2s",
        boxShadow: "0 2px 8px rgba(22,177,255,0.08)"
        // Old version shadow
      };
    }
    function getStatusColor(medal) {
      if (isOwned(medal))
        return "light-green-accent-4";
      const status = medal.purchase_status || "";
      if (status.includes("已过") || status.includes("未到"))
        return "light-blue-accent-4";
      if (status.includes("库存不足"))
        return "orange-darken-1";
      if (status.includes("购买") || status.includes("赠送"))
        return "light-green-accent-4";
      return "grey";
    }
    return (_ctx, _cache) => {
      const _component_v_icon = _resolveComponent("v-icon");
      const _component_v_spacer = _resolveComponent("v-spacer");
      const _component_v_tooltip = _resolveComponent("v-tooltip");
      const _component_v_btn = _resolveComponent("v-btn");
      const _component_v_btn_group = _resolveComponent("v-btn-group");
      const _component_v_card_title = _resolveComponent("v-card-title");
      const _component_v_alert = _resolveComponent("v-alert");
      const _component_v_avatar = _resolveComponent("v-avatar");
      const _component_v_card = _resolveComponent("v-card");
      const _component_v_col = _resolveComponent("v-col");
      const _component_v_row = _resolveComponent("v-row");
      const _component_v_progress_circular = _resolveComponent("v-progress-circular");
      const _component_v_empty_state = _resolveComponent("v-empty-state");
      const _component_v_chip = _resolveComponent("v-chip");
      const _component_v_img = _resolveComponent("v-img");
      const _component_v_slide_group_item = _resolveComponent("v-slide-group-item");
      const _component_v_slide_group = _resolveComponent("v-slide-group");
      const _component_v_tab = _resolveComponent("v-tab");
      const _component_v_tabs = _resolveComponent("v-tabs");
      const _component_v_expand_transition = _resolveComponent("v-expand-transition");
      const _component_v_card_text = _resolveComponent("v-card-text");
      return _openBlock(), _createElementBlock("div", _hoisted_1, [
        (_openBlock(), _createElementBlock("svg", _hoisted_2, [..._cache[3] || (_cache[3] = [
          _createStaticVNode('<defs data-v-f18b27e2><filter id="remove-black-bg" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB" data-v-f18b27e2><feColorMatrix type="luminanceToAlpha" in="SourceGraphic" result="luma" data-v-f18b27e2></feColorMatrix><feComponentTransfer in="luma" result="mask" data-v-f18b27e2><feFuncA type="linear" slope="7" intercept="-0.5" data-v-f18b27e2></feFuncA></feComponentTransfer><feComposite in="SourceGraphic" in2="mask" operator="in" data-v-f18b27e2></feComposite></filter></defs>', 1)
        ])])),
        _createVNode(_component_v_card, {
          flat: "",
          class: "rounded border"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center px-3 py-2 bg-gradient-primary" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-medal-outline",
                  class: "mr-2",
                  color: "white",
                  size: "small"
                }),
                _cache[10] || (_cache[10] = _createElementVNode("span", { class: "text-white" }, "勋章墙 Pro", -1)),
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn_group, {
                  variant: "outlined",
                  density: "compact",
                  class: "mr-1"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: runTask,
                      loading: refreshing.value,
                      size: "small",
                      "min-width": "40",
                      class: "px-0 px-sm-3"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-refresh",
                          size: "18",
                          class: "mr-sm-1"
                        }),
                        _cache[5] || (_cache[5] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "刷新", -1)),
                        _createVNode(_component_v_tooltip, {
                          activator: "parent",
                          location: "bottom"
                        }, {
                          default: _withCtx(() => [..._cache[4] || (_cache[4] = [
                            _createTextVNode("全局刷新", -1)
                          ])]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }, 8, ["loading"]),
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: clearCache,
                      loading: clearingCache.value,
                      size: "small",
                      "min-width": "40",
                      class: "px-0 px-sm-3"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-delete-sweep",
                          size: "18",
                          class: "mr-sm-1"
                        }),
                        _cache[7] || (_cache[7] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "清缓存", -1)),
                        _createVNode(_component_v_tooltip, {
                          activator: "parent",
                          location: "bottom"
                        }, {
                          default: _withCtx(() => [..._cache[6] || (_cache[6] = [
                            _createTextVNode("清理缓存", -1)
                          ])]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }, 8, ["loading"]),
                    _createVNode(_component_v_btn, {
                      color: "white",
                      onClick: notifySwitch,
                      size: "small",
                      "min-width": "40",
                      class: "px-0 px-sm-3"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          icon: "mdi-cog",
                          size: "18",
                          class: "mr-sm-1"
                        }),
                        _cache[8] || (_cache[8] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "设置", -1))
                      ]),
                      _: 1
                    }),
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
                        _cache[9] || (_cache[9] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "关闭", -1))
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
              class: "px-0 py-2",
              style: { "position": "relative" }
            }, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_3, [
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
                _createElementVNode("div", _hoisted_4, [
                  _createVNode(_component_v_row, { dense: "" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_col, {
                        cols: "6",
                        sm: "4",
                        md: ""
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_card, {
                            variant: "tonal",
                            color: "info",
                            class: "pa-3 d-flex align-center rounded-lg"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_avatar, {
                                color: "info",
                                variant: "flat",
                                class: "mr-3",
                                size: "40"
                              }, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_icon, {
                                    color: "white",
                                    icon: "mdi-web"
                                  })
                                ]),
                                _: 1
                              }),
                              _createElementVNode("div", null, [
                                _cache[11] || (_cache[11] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "站点数量", -1)),
                                _createElementVNode("div", _hoisted_5, _toDisplayString(siteCount.value), 1)
                              ])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_col, {
                        cols: "6",
                        sm: "4",
                        md: ""
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_card, {
                            variant: "tonal",
                            color: "primary",
                            class: "pa-3 d-flex align-center rounded-lg"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_avatar, {
                                color: "primary",
                                variant: "flat",
                                class: "mr-3",
                                size: "40"
                              }, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_icon, {
                                    color: "white",
                                    icon: "mdi-medal"
                                  })
                                ]),
                                _: 1
                              }),
                              _createElementVNode("div", null, [
                                _cache[12] || (_cache[12] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "勋章总数", -1)),
                                _createElementVNode("div", _hoisted_6, _toDisplayString(totalMedals.value), 1)
                              ])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_col, {
                        cols: "6",
                        sm: "4",
                        md: ""
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_card, {
                            variant: "tonal",
                            color: "success",
                            class: "pa-3 d-flex align-center rounded-lg"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_avatar, {
                                color: "success",
                                variant: "flat",
                                class: "mr-3",
                                size: "40"
                              }, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_icon, {
                                    color: "white",
                                    icon: "mdi-check-circle"
                                  })
                                ]),
                                _: 1
                              }),
                              _createElementVNode("div", null, [
                                _cache[13] || (_cache[13] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "已拥有", -1)),
                                _createElementVNode("div", _hoisted_7, _toDisplayString(ownedMedals.value), 1)
                              ])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_col, {
                        cols: "6",
                        sm: "4",
                        md: ""
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_card, {
                            variant: "tonal",
                            color: "green",
                            class: "pa-3 d-flex align-center rounded-lg"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_avatar, {
                                color: "green",
                                variant: "flat",
                                class: "mr-3",
                                size: "40"
                              }, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_icon, {
                                    color: "white",
                                    icon: "mdi-cart"
                                  })
                                ]),
                                _: 1
                              }),
                              _createElementVNode("div", null, [
                                _cache[14] || (_cache[14] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "可购买", -1)),
                                _createElementVNode("div", _hoisted_8, _toDisplayString(availableMedals.value), 1)
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
                loading.value && medals.value.length === 0 ? (_openBlock(), _createElementBlock("div", _hoisted_9, [
                  _createVNode(_component_v_progress_circular, {
                    indeterminate: "",
                    color: "primary"
                  }),
                  _cache[15] || (_cache[15] = _createElementVNode("span", { class: "ml-3 text-grey" }, "正在加载勋章数据...", -1))
                ])) : _createCommentVNode("", true),
                !loading.value && medals.value.length === 0 ? (_openBlock(), _createBlock(_component_v_empty_state, {
                  key: 1,
                  icon: "mdi-medal-off-outline",
                  title: "暂无勋章数据",
                  text: "请点击上方刷新按钮获取数据，或检查设置中的站点配置。",
                  class: "py-10"
                })) : _createCommentVNode("", true),
                groupedMedals.value.length > 0 ? (_openBlock(), _createElementBlock("div", _hoisted_10, [
                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groupedMedals.value, (group) => {
                    return _openBlock(), _createElementBlock("div", {
                      key: group.site,
                      class: "mb-6"
                    }, [
                      _createElementVNode("div", _hoisted_11, [
                        _createElementVNode("div", {
                          class: "d-flex align-center",
                          onClick: ($event) => toggleDetails(group.site)
                        }, [
                          _createElementVNode("span", _hoisted_13, _toDisplayString(group.site), 1),
                          group.progress === 100 ? (_openBlock(), _createBlock(_component_v_chip, {
                            key: 0,
                            color: "success",
                            size: "x-small",
                            variant: "flat",
                            class: "font-weight-bold"
                          }, {
                            default: _withCtx(() => [..._cache[16] || (_cache[16] = [
                              _createTextVNode("全收集", -1)
                            ])]),
                            _: 1
                          })) : _createCommentVNode("", true),
                          _createVNode(_component_v_btn, {
                            icon: "mdi-refresh",
                            size: "x-small",
                            variant: "text",
                            color: "primary",
                            loading: refreshingSites.value[group.site],
                            onClick: _withModifiers(($event) => refreshSingleSite(group.site, getSiteIdByName(group.site) || ""), ["stop"]),
                            class: "ml-1"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_icon, null, {
                                default: _withCtx(() => [..._cache[17] || (_cache[17] = [
                                  _createTextVNode("mdi-refresh", -1)
                                ])]),
                                _: 1
                              }),
                              _createVNode(_component_v_tooltip, {
                                activator: "parent",
                                location: "bottom"
                              }, {
                                default: _withCtx(() => [..._cache[18] || (_cache[18] = [
                                  _createTextVNode("单站刷新", -1)
                                ])]),
                                _: 1
                              })
                            ]),
                            _: 1
                          }, 8, ["loading", "onClick"])
                        ], 8, _hoisted_12),
                        _createElementVNode("div", _hoisted_14, [
                          _createElementVNode("span", _hoisted_15, "数量 " + _toDisplayString(group.ownedCount) + "/" + _toDisplayString(group.totalCount), 1),
                          _createElementVNode("span", _hoisted_16, "拥有率 " + _toDisplayString(group.progress) + "%", 1),
                          _createVNode(_component_v_icon, {
                            icon: "mdi-chevron-right",
                            class: _normalizeClass(["ml-1 transition-transform", { "rotate-90": expandedSite.value === group.site }]),
                            onClick: ($event) => toggleDetails(group.site)
                          }, null, 8, ["class", "onClick"])
                        ])
                      ]),
                      (_openBlock(), _createBlock(_component_v_slide_group, {
                        class: "px-2",
                        "show-arrows": "desktop",
                        "selected-class": "",
                        key: group.medals.length
                      }, {
                        default: _withCtx(() => [
                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(group.medals, (medal, index) => {
                            return _openBlock(), _createBlock(_component_v_slide_group_item, {
                              key: index,
                              value: `medal-${index}`
                            }, {
                              default: _withCtx(() => [
                                _createElementVNode("div", {
                                  class: "medal-stack-item",
                                  style: _normalizeStyle([{ "margin": "0 4px" }, getStackItemStyle()])
                                }, [
                                  !isOwned(medal) ? (_openBlock(), _createElementBlock("div", _hoisted_17, " 未拥有 ")) : _createCommentVNode("", true),
                                  _createElementVNode("div", {
                                    class: "d-flex justify-center align-center pt-2 px-2",
                                    style: { "height": "100px" },
                                    onClick: ($event) => toggleDetails(group.site)
                                  }, [
                                    _createVNode(_component_v_img, {
                                      src: getProxiedImageUrl(medal.imageSmall),
                                      class: _normalizeClass(["medal-stack-image", { "circle-mask": needsCircleMask(medal), "remove-black-bg": needsRemoveBlackBg(medal) }]),
                                      contain: "",
                                      "max-height": getMedalSize(medal).stack,
                                      "max-width": getMedalSize(medal).stack,
                                      loading: "lazy"
                                    }, {
                                      placeholder: _withCtx(() => [
                                        _createElementVNode("div", _hoisted_19, [
                                          _createVNode(_component_v_progress_circular, {
                                            indeterminate: "",
                                            color: "grey-lighten-2",
                                            size: "20"
                                          })
                                        ])
                                      ]),
                                      _: 1
                                    }, 8, ["src", "class", "max-height", "max-width"])
                                  ], 8, _hoisted_18),
                                  _createElementVNode("div", {
                                    class: "medal-stack-info",
                                    onClick: ($event) => toggleDetails(group.site)
                                  }, [
                                    _createElementVNode("div", _hoisted_21, _toDisplayString(medal.name), 1)
                                  ], 8, _hoisted_20)
                                ], 4)
                              ]),
                              _: 2
                            }, 1032, ["value"]);
                          }), 128))
                        ]),
                        _: 2
                      }, 1024)),
                      _createVNode(_component_v_expand_transition, null, {
                        default: _withCtx(() => [
                          expandedSite.value === group.site ? (_openBlock(), _createElementBlock("div", _hoisted_22, [
                            hasGroups(group.medals) ? (_openBlock(), _createBlock(_component_v_tabs, {
                              key: 0,
                              modelValue: activeTab.value,
                              "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => activeTab.value = $event),
                              color: "primary",
                              "align-tabs": "start",
                              density: "compact",
                              class: "mb-4"
                            }, {
                              default: _withCtx(() => [
                                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(getGroupNames(group.medals), (groupName) => {
                                  return _openBlock(), _createBlock(_component_v_tab, {
                                    key: groupName,
                                    value: groupName,
                                    class: "text-grey"
                                  }, {
                                    default: _withCtx(() => [
                                      _createTextVNode(_toDisplayString(groupName), 1)
                                    ]),
                                    _: 2
                                  }, 1032, ["value"]);
                                }), 128))
                              ]),
                              _: 2
                            }, 1032, ["modelValue"])) : _createCommentVNode("", true),
                            _createVNode(_component_v_row, { dense: "" }, {
                              default: _withCtx(() => [
                                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(getDisplayMedals(group.medals), (medal, index) => {
                                  return _openBlock(), _createBlock(_component_v_col, {
                                    key: index,
                                    cols: "12",
                                    sm: "6",
                                    md: "4",
                                    xl: "3"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_card, {
                                        class: "mx-auto medal-card medal-item-card h-100 d-flex flex-row pa-2 align-center",
                                        hover: "",
                                        variant: "flat",
                                        elevation: "2",
                                        density: "compact",
                                        style: _normalizeStyle(getCardStyle())
                                      }, {
                                        default: _withCtx(() => [
                                          _createElementVNode("div", {
                                            class: "d-flex justify-center align-center mr-3 flex-shrink-0",
                                            style: _normalizeStyle({ width: getMedalSize(medal).detail + "px", minWidth: getMedalSize(medal).detail + "px" })
                                          }, [
                                            _createVNode(_component_v_img, {
                                              src: getProxiedImageUrl(medal.imageSmall),
                                              "max-height": getMedalSize(medal).detail,
                                              "max-width": getMedalSize(medal).detail,
                                              contain: "",
                                              class: _normalizeClass(["medal-image", { "circle-mask": needsCircleMask(medal), "remove-black-bg": needsRemoveBlackBg(medal) }]),
                                              loading: "lazy"
                                            }, null, 8, ["src", "max-height", "max-width", "class"])
                                          ], 4),
                                          _createElementVNode("div", _hoisted_23, [
                                            _createElementVNode("div", _hoisted_24, [
                                              _createElementVNode("div", _hoisted_25, [
                                                _createElementVNode("div", {
                                                  class: "text-subtitle-2 font-weight-bold text-truncate flex-shrink-1 text-grey-darken-1",
                                                  title: medal.name
                                                }, _toDisplayString(medal.name), 9, _hoisted_26)
                                              ]),
                                              _createElementVNode("div", _hoisted_27, [
                                                medal.bonus_rate ? (_openBlock(), _createBlock(_component_v_chip, {
                                                  key: 0,
                                                  size: "x-small",
                                                  color: "purple-lighten-5",
                                                  variant: "flat",
                                                  class: "px-2 mr-1 font-weight-bold text-purple-darken-2 rounded-pill",
                                                  style: { "height": "20px", "font-size": "11px" }
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createVNode(_component_v_icon, {
                                                      start: "",
                                                      icon: "mdi-star-four-points-outline",
                                                      size: "10",
                                                      class: "mr-1"
                                                    }),
                                                    _createTextVNode(" " + _toDisplayString(medal.bonus_rate), 1)
                                                  ]),
                                                  _: 2
                                                }, 1024)) : _createCommentVNode("", true),
                                                medal.purchase_status ? (_openBlock(), _createBlock(_component_v_chip, {
                                                  key: 1,
                                                  size: "x-small",
                                                  color: getStatusColor(medal),
                                                  variant: "flat",
                                                  class: "px-2 font-weight-bold text-white rounded-pill",
                                                  style: { "height": "20px", "font-size": "11px" }
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createTextVNode(_toDisplayString(isOwned(medal) ? "已拥有" : medal.purchase_status || "未拥有"), 1)
                                                  ]),
                                                  _: 2
                                                }, 1032, ["color"])) : _createCommentVNode("", true)
                                              ])
                                            ]),
                                            _createElementVNode("div", _hoisted_28, [
                                              _createElementVNode("div", _hoisted_29, [
                                                _createTextVNode(_toDisplayString(formatPrice(medal.price)) + " ", 1),
                                                _createElementVNode("span", _hoisted_30, _toDisplayString(getCurrency(medal)), 1)
                                              ])
                                            ]),
                                            _createElementVNode("div", {
                                              class: "text-caption text-grey-darken-1 text-truncate mb-1",
                                              style: { "font-size": "0.65rem !important", "max-width": "100%" },
                                              title: medal.description
                                            }, _toDisplayString(medal.description), 9, _hoisted_31),
                                            _createElementVNode("div", _hoisted_32, [
                                              medal.saleBeginTime ? (_openBlock(), _createElementBlock("div", _hoisted_33, [
                                                _cache[19] || (_cache[19] = _createElementVNode("span", { class: "mr-1 font-weight-bold" }, "开售:", -1)),
                                                _createElementVNode("span", null, _toDisplayString(medal.saleBeginTime), 1)
                                              ])) : _createCommentVNode("", true),
                                              medal.saleEndTime ? (_openBlock(), _createElementBlock("div", _hoisted_34, [
                                                _cache[20] || (_cache[20] = _createElementVNode("span", { class: "mr-1 font-weight-bold" }, "截止:", -1)),
                                                _createElementVNode("span", null, _toDisplayString(medal.saleEndTime), 1)
                                              ])) : _createCommentVNode("", true),
                                              medal.validity ? (_openBlock(), _createElementBlock("div", _hoisted_35, [
                                                _cache[21] || (_cache[21] = _createElementVNode("span", { class: "mr-1 font-weight-bold" }, "有效期:", -1)),
                                                _createElementVNode("span", null, _toDisplayString(medal.validity), 1)
                                              ])) : _createCommentVNode("", true),
                                              medal.new_time ? (_openBlock(), _createElementBlock("div", _hoisted_36, [
                                                _cache[22] || (_cache[22] = _createElementVNode("span", { class: "mr-1 font-weight-bold" }, "上新时间:", -1)),
                                                _createElementVNode("span", null, _toDisplayString(medal.new_time), 1)
                                              ])) : _createCommentVNode("", true),
                                              medal.stock ? (_openBlock(), _createElementBlock("div", _hoisted_37, [
                                                _createVNode(_component_v_icon, {
                                                  icon: "mdi-package-variant-closed",
                                                  size: "10",
                                                  class: "mr-1"
                                                }),
                                                _createElementVNode("span", null, "库存: " + _toDisplayString(medal.stock), 1)
                                              ])) : _createCommentVNode("", true),
                                              medal.stock_status ? (_openBlock(), _createElementBlock("div", _hoisted_38, [
                                                _createVNode(_component_v_chip, {
                                                  size: "x-small",
                                                  color: "orange-lighten-4",
                                                  variant: "flat",
                                                  class: "px-2 font-weight-bold text-orange-darken-4 rounded-pill",
                                                  style: { "height": "18px", "font-size": "10px" }
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createTextVNode(_toDisplayString(medal.stock_status), 1)
                                                  ]),
                                                  _: 2
                                                }, 1024)
                                              ])) : _createCommentVNode("", true)
                                            ])
                                          ])
                                        ]),
                                        _: 2
                                      }, 1032, ["style"])
                                    ]),
                                    _: 2
                                  }, 1024);
                                }), 128))
                              ]),
                              _: 2
                            }, 1024)
                          ])) : _createCommentVNode("", true)
                        ]),
                        _: 2
                      }, 1024)
                    ]);
                  }), 128))
                ])) : _createCommentVNode("", true)
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

const Page_vue_vue_type_style_index_0_scoped_f18b27e2_lang = '';

const Page = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-f18b27e2"]]);

export { Page as default };
