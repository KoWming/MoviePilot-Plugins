import { _ as __vitePreload } from './preload-helper-06b33f0f.js';
import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,mergeProps:_mergeProps,renderList:_renderList,Fragment:_Fragment,normalizeClass:_normalizeClass} = await importShared('vue');

const _hoisted_1 = { class: "as-page" };
const _hoisted_2 = { class: "as-topbar" };
const _hoisted_3 = { class: "as-topbar__left" };
const _hoisted_4 = { class: "as-topbar__icon" };
const _hoisted_5 = {
  key: 0,
  class: "as-topbar__sub"
};
const _hoisted_6 = {
  key: 1,
  class: "as-topbar__sub"
};
const _hoisted_7 = {
  class: "as-topbar__right",
  style: { "padding": "2px" }
};
const _hoisted_8 = {
  key: 0,
  class: "as-results"
};
const _hoisted_9 = { class: "as-result-card as-result-card--down" };
const _hoisted_10 = { class: "as-result-card__value" };
const _hoisted_11 = { class: "as-result-card as-result-card--up" };
const _hoisted_12 = { class: "as-result-card__value" };
const _hoisted_13 = { class: "as-result-card as-result-card--ping" };
const _hoisted_14 = { class: "as-result-card__value" };
const _hoisted_15 = {
  key: 1,
  class: "as-no-data"
};
const _hoisted_16 = {
  key: 2,
  class: "as-server-tag"
};
const _hoisted_17 = {
  key: 3,
  class: "as-card"
};
const _hoisted_18 = { style: { "position": "relative" } };
const _hoisted_19 = {
  class: "as-chart-select",
  style: { "position": "absolute", "left": "8px", "top": "-2px", "z-index": "10" }
};
const _hoisted_20 = {
  key: 4,
  class: "as-card"
};
const _hoisted_21 = { class: "as-card__header" };
const _hoisted_22 = { class: "as-card__badge" };
const _hoisted_23 = { class: "as-table-wrap" };
const _hoisted_24 = { class: "as-table" };
const _hoisted_25 = { class: "as-table__time" };
const _hoisted_26 = { class: "as-table__down" };
const _hoisted_27 = { class: "as-table__up" };
const _hoisted_28 = { class: "as-table__ping" };
const _hoisted_29 = { class: "as-table__server" };
const _hoisted_30 = {
  class: "as-table__server",
  style: { "color": "grey", "font-size": "11px" }
};
const _hoisted_31 = {
  key: 0,
  class: "as-pagination"
};
const _hoisted_32 = ["disabled"];
const _hoisted_33 = { class: "as-pg-info" };
const _hoisted_34 = ["disabled"];
const {ref,reactive,computed,onMounted,onBeforeUnmount,nextTick} = await importShared('vue');

const pageSize = 10;
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Page",
  props: {
    api: { type: Object, default: () => ({}) }
  },
  emits: ["action", "switch", "close"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const status = reactive({ enabled: false, running: false, latest: null, last_run: null });
    const latest = ref(null);
    const history = ref([]);
    const historyTotal = ref(0);
    const historyDays = ref(7);
    const loading = reactive({ status: false, run: false, history: false });
    const snackbar = reactive({ show: false, text: "", color: "success" });
    const chartContainer = ref(null);
    let chartInstance = null;
    let pollingTimer = null;
    const dayOptions = [
      { label: "7天", value: 7 },
      { label: "30天", value: 30 },
      { label: "全部", value: 0 }
    ];
    const page = ref(1);
    const pagedHistory = computed(() => {
      const start = (page.value - 1) * pageSize;
      return [...history.value].reverse().slice(start, start + pageSize);
    });
    const totalPages = computed(() => Math.ceil(history.value.length / pageSize));
    async function fetchStatus() {
      loading.status = true;
      try {
        const res = await props.api.get("plugin/AutoSpeed/status");
        Object.assign(status, res);
        if (res.latest)
          latest.value = res.latest;
      } catch (e) {
        console.warn("fetchStatus error", e);
      } finally {
        loading.status = false;
      }
    }
    async function fetchHistory() {
      loading.history = true;
      try {
        const res = await props.api.get(`plugin/AutoSpeed/history?days=${historyDays.value}`);
        history.value = res.records || [];
        historyTotal.value = res.total || 0;
        page.value = 1;
        await nextTick();
        renderChart();
      } catch (e) {
        console.warn("fetchHistory error", e);
      } finally {
        loading.history = false;
      }
    }
    async function fetchLatest() {
      try {
        const res = await props.api.get("plugin/AutoSpeed/latest");
        if (res.has_data)
          latest.value = res.record;
      } catch (e) {
        console.warn("fetchLatest error", e);
      }
    }
    async function runSpeedtest() {
      if (loading.run)
        return;
      loading.run = true;
      try {
        const res = await props.api.post("plugin/AutoSpeed/run", {});
        showSnack(res.msg || "测速已开始", "success");
        startPolling();
      } catch (e) {
        showSnack("触发测速失败", "error");
      } finally {
        loading.run = false;
      }
    }
    function startPolling() {
      stopPolling();
      let maxPolls = 30;
      pollingTimer = setInterval(async () => {
        await fetchStatus();
        maxPolls--;
        if (!status.running || maxPolls <= 0) {
          stopPolling();
          await fetchLatest();
          await fetchHistory();
          emit("action");
        }
      }, 5e3);
    }
    function stopPolling() {
      if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
      }
    }
    async function renderChart() {
      if (!chartContainer.value || history.value.length === 0)
        return;
      try {
        const echarts = await __vitePreload(() => import('./index-cf12311a.js'),true?[]:void 0);
        if (!chartInstance) {
          chartInstance = echarts.init(chartContainer.value);
        }
        const sorted = [...history.value].sort(
          (a, b) => a.timestamp.localeCompare(b.timestamp)
        );
        const timestamps = sorted.map((r) => r.timestamp.slice(5, 16));
        const downloads = sorted.map((r) => r.download);
        const uploads = sorted.map((r) => r.upload);
        const pings = sorted.map((r) => r.ping);
        const isDark = document.documentElement.getAttribute("data-theme") === "dark" || document.documentElement.classList.contains("v-theme--dark") || window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        const textColor = isDark ? "#aaaaaa" : "#666666";
        const splitLineColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
        const tooltipBg = isDark ? "rgba(30,30,40,0.85)" : "rgba(255,255,255,0.95)";
        const tooltipBorder = isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.1)";
        const tooltipText = isDark ? "#ffffff" : "#333333";
        const option = {
          backgroundColor: "transparent",
          tooltip: {
            trigger: "axis",
            backgroundColor: tooltipBg,
            borderColor: tooltipBorder,
            textStyle: { color: tooltipText, fontSize: 12 },
            formatter: (params) => {
              const t = params[0].axisValue;
              const lines = params.map(
                (p) => {
                  const unit = p.seriesName === "延迟" ? "ms" : "Mbps";
                  return `<span style="color:${p.color}">●</span> <span style="color:${tooltipText}">${p.seriesName}: <b>${p.value} ${unit}</b></span>`;
                }
              );
              return `<div style="font-size:11px;color:${textColor};margin-bottom:4px;">${t}</div>${lines.join("<br/>")}`;
            }
          },
          legend: {
            data: ["下行", "上行", "延迟"],
            textStyle: { color: textColor, fontSize: 10 },
            itemWidth: 12,
            itemHeight: 8,
            itemGap: 8,
            top: 2,
            right: 8
          },
          grid: { left: "1%", right: "3%", bottom: "4%", top: "60px", containLabel: true },
          xAxis: {
            type: "category",
            data: timestamps,
            axisLabel: {
              color: textColor,
              fontSize: 10,
              rotate: 30,
              interval: Math.floor(timestamps.length / 6)
            },
            axisLine: { lineStyle: { color: splitLineColor } },
            splitLine: { show: false }
          },
          yAxis: [
            {
              type: "value",
              name: "Mbps",
              nameTextStyle: { color: textColor, fontSize: 10 },
              axisLabel: { color: textColor, fontSize: 10 },
              splitLine: { lineStyle: { color: splitLineColor, type: "dashed" } }
            },
            {
              type: "value",
              name: "ms",
              nameTextStyle: { color: textColor, fontSize: 10 },
              axisLabel: { color: textColor, fontSize: 10 },
              splitLine: { show: false }
            }
          ],
          series: [
            {
              name: "下行",
              type: "line",
              data: downloads,
              smooth: true,
              yAxisIndex: 0,
              lineStyle: { color: "#a78bfa", width: 2 },
              itemStyle: { color: "#a78bfa" },
              areaStyle: {
                color: {
                  type: "linear",
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [{ offset: 0, color: "rgba(167,139,250,0.25)" }, { offset: 1, color: "rgba(167,139,250,0)" }]
                }
              },
              showSymbol: false
            },
            {
              name: "上行",
              type: "line",
              data: uploads,
              smooth: true,
              yAxisIndex: 0,
              lineStyle: { color: "#34d399", width: 2 },
              itemStyle: { color: "#34d399" },
              areaStyle: {
                color: {
                  type: "linear",
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [{ offset: 0, color: "rgba(52,211,153,0.2)" }, { offset: 1, color: "rgba(52,211,153,0)" }]
                }
              },
              showSymbol: false
            },
            {
              name: "延迟",
              type: "line",
              data: pings,
              smooth: true,
              yAxisIndex: 1,
              lineStyle: { color: "#fbbf24", width: 1.5, type: "dashed" },
              itemStyle: { color: "#fbbf24" },
              showSymbol: false
            }
          ]
        };
        chartInstance.setOption(option, true);
      } catch (e) {
        console.warn("ECharts error", e);
      }
    }
    function showSnack(text, color = "success") {
      snackbar.text = text;
      snackbar.color = color;
      snackbar.show = true;
    }
    async function selectDays(days) {
      historyDays.value = days;
      await fetchHistory();
    }
    onMounted(async () => {
      await fetchStatus();
      await fetchLatest();
      await fetchHistory();
    });
    onBeforeUnmount(() => {
      stopPolling();
      if (chartInstance) {
        chartInstance.dispose();
        chartInstance = null;
      }
    });
    return (_ctx, _cache) => {
      const _component_v_icon = _resolveComponent("v-icon");
      const _component_v_btn = _resolveComponent("v-btn");
      const _component_v_btn_group = _resolveComponent("v-btn-group");
      const _component_v_list_item_title = _resolveComponent("v-list-item-title");
      const _component_v_list_item = _resolveComponent("v-list-item");
      const _component_v_list = _resolveComponent("v-list");
      const _component_v_menu = _resolveComponent("v-menu");
      const _component_v_snackbar = _resolveComponent("v-snackbar");
      return _openBlock(), _createElementBlock("div", _hoisted_1, [
        _createElementVNode("div", _hoisted_2, [
          _createElementVNode("div", _hoisted_3, [
            _createElementVNode("div", _hoisted_4, [
              _createVNode(_component_v_icon, {
                icon: "mdi-speedometer",
                size: "24"
              })
            ]),
            _createElementVNode("div", null, [
              _cache[5] || (_cache[5] = _createElementVNode("div", { class: "as-topbar__title" }, "网络测速", -1)),
              status.last_run ? (_openBlock(), _createElementBlock("div", _hoisted_5, " 上次测速：" + _toDisplayString(status.last_run), 1)) : (_openBlock(), _createElementBlock("div", _hoisted_6, "从未运行"))
            ])
          ]),
          _createElementVNode("div", _hoisted_7, [
            _createVNode(_component_v_btn_group, {
              variant: "tonal",
              density: "compact",
              class: "elevation-0"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  onClick: runSpeedtest,
                  loading: loading.run || status.running,
                  size: "small",
                  "min-width": "40",
                  class: "px-0 px-sm-3"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_icon, {
                      icon: "mdi-play",
                      size: "18",
                      class: "mr-sm-1"
                    }),
                    _cache[6] || (_cache[6] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "测速", -1))
                  ]),
                  _: 1
                }, 8, ["loading"]),
                _createVNode(_component_v_btn, {
                  color: "primary",
                  onClick: _cache[0] || (_cache[0] = ($event) => emit("switch", "Config")),
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
                    _cache[7] || (_cache[7] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "设置", -1))
                  ]),
                  _: 1
                }),
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
                    _cache[8] || (_cache[8] = _createElementVNode("span", { class: "btn-text d-none d-sm-inline" }, "关闭", -1))
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ])
        ]),
        latest.value ? (_openBlock(), _createElementBlock("div", _hoisted_8, [
          _createElementVNode("div", _hoisted_9, [
            _cache[9] || (_cache[9] = _createElementVNode("div", { class: "as-result-card__label" }, "下行速度", -1)),
            _createElementVNode("div", _hoisted_10, _toDisplayString(latest.value.download), 1),
            _cache[10] || (_cache[10] = _createElementVNode("div", { class: "as-result-card__unit" }, "Mbps", -1))
          ]),
          _createElementVNode("div", _hoisted_11, [
            _cache[11] || (_cache[11] = _createElementVNode("div", { class: "as-result-card__label" }, "上行速度", -1)),
            _createElementVNode("div", _hoisted_12, _toDisplayString(latest.value.upload), 1),
            _cache[12] || (_cache[12] = _createElementVNode("div", { class: "as-result-card__unit" }, "Mbps", -1))
          ]),
          _createElementVNode("div", _hoisted_13, [
            _cache[13] || (_cache[13] = _createElementVNode("div", { class: "as-result-card__label" }, "网络延迟", -1)),
            _createElementVNode("div", _hoisted_14, _toDisplayString(latest.value.ping), 1),
            _cache[14] || (_cache[14] = _createElementVNode("div", { class: "as-result-card__unit" }, "ms", -1))
          ])
        ])) : (_openBlock(), _createElementBlock("div", _hoisted_15, [..._cache[15] || (_cache[15] = [
          _createElementVNode("span", null, '暂无测速数据，点击"立即测速"开始', -1)
        ])])),
        latest.value?.server_name ? (_openBlock(), _createElementBlock("div", _hoisted_16, " 📡 " + _toDisplayString(latest.value.server_name) + "  ·  " + _toDisplayString(latest.value.timestamp), 1)) : _createCommentVNode("", true),
        history.value.length > 0 ? (_openBlock(), _createElementBlock("div", _hoisted_17, [
          _createElementVNode("div", _hoisted_18, [
            _createElementVNode("div", _hoisted_19, [
              _createVNode(_component_v_menu, {
                location: "bottom start",
                offset: 4
              }, {
                activator: _withCtx(({ props: props2 }) => [
                  _createElementVNode("div", _mergeProps({ class: "as-chart-select-btn" }, props2), [
                    _createTextVNode(_toDisplayString(dayOptions.find((opt) => opt.value === historyDays.value)?.label) + " ", 1),
                    _createVNode(_component_v_icon, {
                      icon: "mdi-chevron-down",
                      size: "14",
                      class: "ml-1 opacity-70"
                    })
                  ], 16)
                ]),
                default: _withCtx(() => [
                  _createVNode(_component_v_list, {
                    density: "compact",
                    class: "py-1",
                    "bg-color": "surface",
                    elevation: "4"
                  }, {
                    default: _withCtx(() => [
                      (_openBlock(), _createElementBlock(_Fragment, null, _renderList(dayOptions, (opt) => {
                        return _createVNode(_component_v_list_item, {
                          key: opt.value,
                          onClick: ($event) => selectDays(opt.value),
                          active: historyDays.value === opt.value,
                          color: "primary",
                          "min-height": "32"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list_item_title, { style: { "font-size": "13px", "font-weight": "500" } }, {
                              default: _withCtx(() => [
                                _createTextVNode(_toDisplayString(opt.label), 1)
                              ]),
                              _: 2
                            }, 1024)
                          ]),
                          _: 2
                        }, 1032, ["onClick", "active"]);
                      }), 64))
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _createElementVNode("div", {
              ref_key: "chartContainer",
              ref: chartContainer,
              class: "as-chart"
            }, null, 512)
          ])
        ])) : _createCommentVNode("", true),
        history.value.length > 0 ? (_openBlock(), _createElementBlock("div", _hoisted_20, [
          _createElementVNode("div", _hoisted_21, [
            _cache[16] || (_cache[16] = _createElementVNode("span", { class: "as-card__title" }, "📋 历史记录", -1)),
            _createElementVNode("span", _hoisted_22, _toDisplayString(historyTotal.value) + " 条", 1)
          ]),
          _createElementVNode("div", _hoisted_23, [
            _createElementVNode("table", _hoisted_24, [
              _cache[20] || (_cache[20] = _createElementVNode("thead", null, [
                _createElementVNode("tr", null, [
                  _createElementVNode("th", null, "时间"),
                  _createElementVNode("th", null, "下行"),
                  _createElementVNode("th", null, "上行"),
                  _createElementVNode("th", null, "延迟"),
                  _createElementVNode("th", null, "节点名称"),
                  _createElementVNode("th", null, "节点 ID")
                ])
              ], -1)),
              _createElementVNode("tbody", null, [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(pagedHistory.value, (row, idx) => {
                  return _openBlock(), _createElementBlock("tr", {
                    key: row.timestamp,
                    class: _normalizeClass({ "as-table__row--alt": idx % 2 === 1 })
                  }, [
                    _createElementVNode("td", _hoisted_25, _toDisplayString(row.timestamp), 1),
                    _createElementVNode("td", _hoisted_26, [
                      _createTextVNode(_toDisplayString(row.download) + " ", 1),
                      _cache[17] || (_cache[17] = _createElementVNode("span", null, "Mbps", -1))
                    ]),
                    _createElementVNode("td", _hoisted_27, [
                      _createTextVNode(_toDisplayString(row.upload) + " ", 1),
                      _cache[18] || (_cache[18] = _createElementVNode("span", null, "Mbps", -1))
                    ]),
                    _createElementVNode("td", _hoisted_28, [
                      _createTextVNode(_toDisplayString(row.ping) + " ", 1),
                      _cache[19] || (_cache[19] = _createElementVNode("span", null, "ms", -1))
                    ]),
                    _createElementVNode("td", _hoisted_29, _toDisplayString(row.server_name), 1),
                    _createElementVNode("td", _hoisted_30, "#" + _toDisplayString(row.server_id), 1)
                  ], 2);
                }), 128))
              ])
            ])
          ]),
          totalPages.value > 1 ? (_openBlock(), _createElementBlock("div", _hoisted_31, [
            _createElementVNode("button", {
              class: "as-pg-btn",
              disabled: page.value <= 1,
              onClick: _cache[2] || (_cache[2] = ($event) => page.value--)
            }, "‹", 8, _hoisted_32),
            _createElementVNode("span", _hoisted_33, _toDisplayString(page.value) + " / " + _toDisplayString(totalPages.value), 1),
            _createElementVNode("button", {
              class: "as-pg-btn",
              disabled: page.value >= totalPages.value,
              onClick: _cache[3] || (_cache[3] = ($event) => page.value++)
            }, "›", 8, _hoisted_34)
          ])) : _createCommentVNode("", true)
        ])) : _createCommentVNode("", true),
        _createVNode(_component_v_snackbar, {
          modelValue: snackbar.show,
          "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => snackbar.show = $event),
          color: snackbar.color,
          timeout: "3000",
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

const Page_vue_vue_type_style_index_0_scoped_99391e6a_lang = '';

const Page = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-99391e6a"]]);

export { Page as default };
