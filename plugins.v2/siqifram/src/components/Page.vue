<template>
  <div class="siqi-page">
    <div class="siqi-topbar">
      <div class="siqi-topbar__left">
        <div class="siqi-topbar__icon">
          <v-icon icon="mdi-sprout" size="24" />
        </div>
        <div>
          <div class="siqi-topbar__title">思齐农场</div>
        <!-- 一键点赞 - 二级页面 -->
        <v-dialog v-model="showLikeDialog" max-width="680" scrollable>
          <v-card class="neu-visit-dialog like-dialog" flat>
            <v-card-title class="neu-visit-header">
              <div class="neu-visit-avatar like-avatar">👍</div>
              <div class="neu-visit-info">
                <div class="neu-visit-name">一键点赞</div>
                <div class="neu-visit-decor">按用户名顺序点赞，直到次数用完</div>
              </div>
              <div class="neu-visit-actions">
                <v-btn icon variant="text" size="small" @click="showLikeDialog = false">
                  <v-icon icon="mdi-close" color="grey" />
                </v-btn>
              </div>
            </v-card-title>
            <v-card-text>
              <div class="like-panel">
                <div class="like-panel-head">
                  <div class="like-panel-title">⚡ 点赞名单</div>
                  <v-chip v-if="likeMax > 0" size="small" color="pink" variant="tonal">剩余 {{ likeRemaining ?? '-' }}/{{ likeMax }}</v-chip>
                </div>
                <v-textarea v-model="likeUsernames" rows="5" auto-grow variant="outlined" density="compact" hide-details placeholder="请输入用户名（逗号或换行分隔）" class="like-textarea" />
                <div class="like-status">
                  <template v-if="likeMax <= 0">可填写多个用户名（逗号或换行分隔），按顺序点赞直到次数用完</template>
                  <template v-else-if="Number(likeRemaining || 0) > 0">剩余次数：{{ likeRemaining }}/{{ likeMax }}（按顺序点赞直到次数用完）</template>
                  <template v-else>剩余次数：0/{{ likeMax }}，{{ formatHms(likeNextIn) }} 后可再次点赞</template>
                </div>
                <div v-if="likeLikedList.length" class="today-liked">
                  <div class="today-liked-title">今日已点赞</div>
                  <div v-for="row in likeLikedList" :key="`${row.to_username}-${row.created_at || row.to_userid || ''}`" class="today-liked-item">
                    <span class="u">{{ row.to_username || '-' }}</span>
                    <span class="r">对方 +{{ Number(row.owner_reward || 0) }} / 你 +{{ Number(row.visitor_reward || 0) }}</span>
                  </div>
                </div>
                <div class="like-actions">
                  <v-btn variant="tonal" color="primary" @click="loadLikeTargets" :loading="likeLoading">随机填充</v-btn>
                  <v-btn color="pink" @click="submitLikeBatch" :loading="likeLoading" :disabled="!likeUsernames.trim() || Number(likeRemaining || 0) <= 0">👍 一键点赞</v-btn>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-dialog>

        <!-- 偷菜目标展示 - 二级页面 -->
        <v-dialog v-model="showStealDialog" max-width="760" scrollable>
          <v-card class="neu-visit-dialog" flat>
            <v-card-title class="neu-visit-header">
              <div class="neu-visit-avatar steal-avatar">🥷</div>
              <div class="neu-visit-info">
                <div class="neu-visit-name">
                  {{ stealTarget.victim_desc_name || stealTarget.victim_name || '偷菜目标' }}
                  <v-chip v-if="stealTarget.ready_plots_count" size="x-small" color="red" class="ml-2" variant="flat">
                    成熟 {{ stealTarget.ready_plots_count }}
                  </v-chip>
                </div>
                <div class="neu-visit-decor">
                  今日可偷 {{ stealTarget.max_steal_count || 0 }} 个，已偷 {{ Number(stealTarget.steal_count_today || 0) + stolenCount }} 个
                </div>
              </div>
              <div class="neu-visit-actions">
                <v-btn v-if="stolenCount > 0" color="success" variant="tonal" size="small" @click="finishStealing" :loading="stealLoading">完成</v-btn>
                <v-btn icon variant="text" size="small" @click="closeStealDialog">
                  <v-icon icon="mdi-close" color="grey" />
                </v-btn>
              </div>
            </v-card-title>
            <v-card-text style="max-height:62vh;">
              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                点击成熟作物进行偷菜；可偷数量由发种等级和 HNR 值决定。
              </v-alert>
              <div v-if="!(stealTarget.victim_lands || []).length" class="neu-visit-empty">暂无可展示农场</div>
              <div v-for="land in stealTarget.victim_lands || []" :key="'sl-'+land.id" class="steal-land-section">
                <div class="steal-land-title">{{ land.name || '农场' }} <span class="text-caption text-grey">坑位：{{ land.effective_plot_count || land.plot_count || 0 }}</span></div>
                <div v-if="land.unlocked !== undefined && !Number(land.unlocked)" class="steal-land-locked">未解锁</div>
                <div v-else class="steal-plot-grid">
                  <button v-for="plot in stealPlotsForLand(land)" :key="'sp-'+land.id+'-'+plot.plot_index" class="steal-plot" :class="stealPlotClass(plot)" @click="stealPlotAction(land, plot)" :disabled="!isStealablePlot(plot) || plot.stolen || stealLoading">
                    <template v-if="plot.seed_id">
                      <img v-if="getStealStageImg(plot)" :src="getStealStageImg(plot)" class="stage-img-sm" :alt="plot.seed_name || ''">
                      <span v-else class="neu-plot-emoji">{{ plot.seed_icon || seedById(plot.seed_id)?.icon || '🌱' }}</span>
                      <small>{{ plot.seed_name || seedById(plot.seed_id)?.name || '' }}</small>
                      <span v-if="plot.stolen" class="steal-badge stolen">已偷</span>
                      <span v-else-if="isStealablePlot(plot)" class="steal-badge ready">可偷</span>
                    </template>
                    <template v-else>
                      <span class="neu-plot-empty-icon">🌱</span>
                      <small class="text-grey">空地</small>
                    </template>
                  </button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-dialog>

        <!-- 购买坑位确认 -->
        <v-dialog v-model="showBuyPlotConfirmDialog" max-width="520">
          <v-card class="neu-visit-dialog sell-confirm-dialog" flat>
            <v-card-title class="neu-visit-header">
              <div class="neu-visit-avatar buy-avatar">🏪</div>
              <div class="neu-visit-info">
                <div class="neu-visit-name">确认购买坑位</div>
                <div class="neu-visit-decor">购买后将解锁当前农场的下一个可用坑位</div>
              </div>
              <div class="neu-visit-actions">
                <v-btn icon variant="text" size="small" @click="showBuyPlotConfirmDialog = false">
                  <v-icon icon="mdi-close" color="grey" />
                </v-btn>
              </div>
            </v-card-title>
            <v-card-text>
              <div class="sell-confirm-summary">
                <div class="sell-confirm-stat"><span>购买农场</span><b>{{ pendingBuyPlot?.land?.name || '-' }}</b><small>坑位 +1</small></div>
                <div class="sell-confirm-stat"><span>消耗魔力</span><b>{{ Number(pendingBuyPlot?.plot?.cost || 0) }}</b><small>魔力</small></div>
              </div>
              <div class="buy-confirm-tip">
                确认购买 {{ pendingBuyPlot?.land?.name || '当前农场' }} 的下一个坑位吗？购买成功后会自动刷新菜地数据。
              </div>
              <div class="sell-confirm-actions">
                <v-btn variant="flat" class="sell-confirm-cancel" @click="showBuyPlotConfirmDialog = false">取消</v-btn>
                <v-btn variant="flat" class="sell-confirm-submit" :loading="loading" @click="confirmBuyPlotSlot">
                  <v-icon icon="mdi-plus-box" size="16" class="mr-1" />确认购买
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-dialog>

        <!-- 一键出售确认 -->
        <v-dialog v-model="showSellConfirmDialog" max-width="520">
          <v-card class="neu-visit-dialog sell-confirm-dialog" flat>
            <v-card-title class="neu-visit-header">
              <div class="neu-visit-avatar sell-avatar">💰</div>
              <div class="neu-visit-info">
                <div class="neu-visit-name">确认一键出售</div>
                <div class="neu-visit-decor">出售前请确认背包库存与预计收益</div>
              </div>
              <div class="neu-visit-actions">
                <v-btn icon variant="text" size="small" @click="showSellConfirmDialog = false">
                  <v-icon icon="mdi-close" color="grey" />
                </v-btn>
              </div>
            </v-card-title>
            <v-card-text>
              <div class="sell-confirm-summary">
                <div class="sell-confirm-stat"><span>出售物品</span><b>{{ sellAllSummary.totalQuantity }}</b><small>份</small></div>
                <div class="sell-confirm-stat"><span>预计获得</span><b>{{ sellAllSummary.totalReward }}</b><small>魔力</small></div>
              </div>
              <div class="sell-confirm-list">
                <div v-for="item in sellAllItems" :key="`sell-${item.seed_id}`" class="sell-confirm-item">
                  <span>{{ item.icon || '🌱' }} {{ item.name || `作物 ${item.seed_id}` }}</span>
                  <em>{{ Number(item.quantity || 0) }} × {{ inventoryUnitReward(item) }} = {{ Number(item.quantity || 0) * inventoryUnitReward(item) }}</em>
                </div>
              </div>
              <div class="sell-confirm-actions">
                <v-btn variant="flat" class="sell-confirm-cancel" @click="showSellConfirmDialog = false">取消</v-btn>
                <v-btn variant="flat" class="sell-confirm-submit" :loading="loading" @click="confirmSellAll">
                  <v-icon icon="mdi-cash-sync" size="16" class="mr-1" />确认出售
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-dialog>

          <div class="siqi-topbar__sub">管理菜地、背包、偷菜与农场互动</div>
        </div>
      </div>
      <div class="siqi-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="success" size="small" min-width="40" class="px-0 px-sm-3" @click="refresh(true)" :loading="loading">
            <v-icon icon="mdi-refresh" size="18" class="mr-sm-1" />
            <span class="d-none d-sm-inline">刷新</span>
          </v-btn>
          <v-btn color="success" size="small" min-width="40" class="px-0 px-sm-3" @click="$emit('switch', 'config')">
            <v-icon icon="mdi-cog" size="18" class="mr-sm-1" />
            <span class="d-none d-sm-inline">配置</span>
          </v-btn>
          <v-btn color="success" size="small" min-width="40" class="px-0 px-sm-3" @click="$emit('close')">
            <v-icon icon="mdi-close" size="18" class="mr-sm-1" />
            <span class="d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <div class="siqi-content">
      <v-alert v-if="message" :type="messageType" density="compact" class="siqi-toast" closable @click:close="message=''">{{ message }}</v-alert>

      <div v-if="initialLoading" class="page-skeleton">
        <v-row dense class="mb-3">
          <v-col v-for="i in 4" :key="'sk-stat-'+i" cols="6" md="3"><div class="stat-card skeleton-stat"><div class="sk sk-icon"></div><div class="sk-lines"><div class="sk sk-line short"></div><div class="sk sk-line"></div></div></div></v-col>
        </v-row>
        <div class="seed-interact-row mb-3">
          <v-card flat class="siqi-card seed-shop-card skeleton-shell"><v-card-title class="siqi-card-title"><div class="sk sk-title"></div><v-spacer /><div class="sk sk-button"></div></v-card-title><v-card-text class="seed-shop-body"><div class="seed-grid"><div v-for="i in 6" :key="'sk-seed-'+i" class="sk sk-seed"></div></div></v-card-text></v-card>
          <v-card flat class="siqi-card farm-interact-card skeleton-shell"><v-card-title class="siqi-card-title"><div class="sk sk-title"></div></v-card-title><v-card-text class="farm-interact-body"><div class="skeleton-actions"><div v-for="i in 3" :key="'sk-action-'+i" class="sk sk-action"></div></div></v-card-text></v-card>
        </div>
        <v-card flat class="siqi-card mb-3 skeleton-shell"><v-card-title class="siqi-card-title siqi-card-title--farm"><div class="sk sk-title"></div><v-spacer /><div class="sk sk-button"></div></v-card-title><v-card-text class="land-body"><div class="land-section"><div class="sk sk-title"></div><div class="plot-grid mt-3"><div v-for="i in 10" :key="'sk-plot-'+i" class="sk sk-plot"></div></div></div></v-card-text></v-card>
        <v-row dense><v-col cols="12" md="6"><v-card flat class="siqi-card h-100 skeleton-shell"><v-card-title class="siqi-card-title siqi-card-title--inventory"><div class="sk sk-title"></div></v-card-title><v-card-text><div v-for="i in 4" :key="'sk-inv-'+i" class="sk sk-row"></div></v-card-text></v-card></v-col><v-col cols="12" md="6"><v-card flat class="siqi-card h-100 skeleton-shell"><v-card-title class="siqi-card-title siqi-card-title--logs"><div class="sk sk-title"></div></v-card-title><v-card-text class="history-body"><div v-for="i in 5" :key="'sk-log-'+i" class="sk sk-row"></div></v-card-text></v-card></v-col></v-row>
      </div>

      <template v-else>

      <v-row dense class="mb-3">
        <v-col cols="6" md="3"><stat-card title="魔力值" :value="farm.user_bonus ?? '-'" icon="mdi-auto-fix" color="orange" /></v-col>
        <v-col cols="6" md="3"><stat-card title="总种植收获" :value="farm.user_stats?.total_harvest ?? '-'" icon="mdi-sprout" color="green" /></v-col>
        <v-col cols="6" md="3"><stat-card title="总偷菜收获" :value="farm.user_steal_gain ?? farm.user_stats?.total_steal_gain ?? '-'" icon="mdi-incognito" color="red" /></v-col>
        <v-col cols="6" md="3"><stat-card title="农场被点赞" :value="farm.user_farm_like_total ?? farm.farm_like_total ?? '-'" icon="mdi-thumb-up" color="blue" /></v-col>
      </v-row>

      <div class="seed-interact-row mb-3">
        <v-card flat class="siqi-card seed-shop-card">
          <v-card-title class="siqi-card-title d-flex align-center">
            <v-icon icon="mdi-seed" class="mr-2" color="green" />种子商店
            <v-spacer />
            <v-btn color="green" size="small" class="quick-action-btn quick-action-btn--plant" :disabled="!selectedSeed" @click="plantFill">一键种植</v-btn>
          </v-card-title>
          <v-card-text class="seed-shop-body">
            <div class="seed-grid">
              <button v-for="seed in farm.seeds || []" :key="seed.id" class="seed" :class="{selected: selectedSeed === String(seed.id), locked: !isSeedUnlocked(seed)}" @click="selectSeed(seed)">
                <div class="seed-icon">{{ seed.icon }}</div>
                <div class="seed-main">
                  <div class="seed-name">{{ seed.name }}</div>
                  <div class="seed-meta">{{ seed.cost }} → {{ seed.base_reward }} · {{ formatSeconds(seed.grow_time) }}</div>
                </div>
                <div v-if="!isSeedUnlocked(seed)" class="seed-lock" :title="`需${seed.unlock_harvest}收获分解锁`">{{ seed.unlock_harvest }}收获分</div>
              </button>
            </div>
          </v-card-text>
        </v-card>

        <v-card flat class="siqi-card farm-interact-card">
          <v-card-title class="siqi-card-title d-flex align-center">
            <v-icon icon="mdi-home-group" class="mr-2" color="deep-purple" />农场互动
            <span class="farm-interact-subtitle">偷菜、点赞与参观</span>
          </v-card-title>
          <v-card-text class="farm-interact-body">
            <v-row dense class="farm-action-list">
              <v-col cols="12">
                <div class="neu-action-card neu-action-card--steal">
                  <div class="neu-action-icon">🥷</div>
                  <div class="neu-action-content">
                    <div class="neu-action-label">偷菜</div>
                    <div class="neu-action-desc">每日一次，自动寻找可偷作物</div>
                  </div>
                  <v-btn :color="farm.can_steal ? 'red' : 'grey'" size="small" @click="steal" :disabled="!farm.can_steal" class="neu-btn farm-action-btn quick-action-btn quick-action-btn--steal">
                    {{ farm.can_steal ? '去偷菜' : '今日已偷' }}
                  </v-btn>
                </div>
              </v-col>
              <v-col cols="12">
                <div class="neu-action-card neu-action-card--like">
                  <div class="neu-action-icon">👍</div>
                  <div class="neu-action-content">
                    <div class="neu-action-label">一键点赞</div>
                    <div class="neu-action-desc">随机填充目标并批量点赞</div>
                  </div>
                  <v-btn color="pink" size="small" @click="openLikeDialog" :loading="likeLoading" class="neu-btn farm-action-btn quick-action-btn quick-action-btn--like">
                    去点赞
                  </v-btn>
                </div>
              </v-col>
              <v-col cols="12">
                <div class="neu-action-card neu-action-card--visit">
                  <div class="neu-action-icon">🚜</div>
                  <div class="neu-action-content">
                    <div class="neu-action-label">参观农场</div>
                    <div class="neu-action-desc">输入用户名或随机访问</div>
                  </div>
                  <div class="visit-action-row">
                    <v-text-field v-model="visitUsername" density="compact" hide-details placeholder="用户名" variant="outlined" class="visit-username-input flex-grow-1" />
                    <v-btn color="purple" size="small" @click="visitFarm" :loading="visiting" :disabled="!visitUsername.trim()" class="visit-btn farm-action-btn quick-action-btn quick-action-btn--visit">
                      访问农场
                    </v-btn>
                    <v-btn color="deep-purple" size="small" @click="visitRandom" :loading="visiting" class="visit-btn farm-action-btn quick-action-btn quick-action-btn--random">
                      随机访问
                    </v-btn>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </div>

      <v-card flat class="siqi-card mb-3">
        <v-card-title class="siqi-card-title siqi-card-title--farm d-flex align-center">
          <v-icon icon="mdi-farm" class="mr-2" color="brown" />菜地
          <v-spacer />
          <v-btn color="orange" size="small" class="quick-action-btn quick-action-btn--harvest" @click="harvestAllOCR" :loading="loadingOCR">一键收获</v-btn>
        </v-card-title>
        <v-card-text class="land-body">
          <div v-for="land in farm.lands || []" :key="land.id" class="land-section" :class="{'land-section--locked': !landUnlocked(land)}">
            <div class="land-title">{{ land.name }}<span class="land-plot-count">（坑位：{{ landPlotCountLabel(land) }}）</span> <span class="text-caption text-grey">{{ landUnlocked(land) ? '' : `解锁需总收获 ${land.unlock_harvest}` }}</span></div>
            <div v-if="!landUnlocked(land)" class="land-locked-mobile-hint">未解锁，移动端已折叠显示</div>
            <div class="plot-grid">
              <button v-for="plot in plotsForLand(land)" :key="`${land.id}-${plot.plot_index}`" class="plot" :class="plotClass(plot)" :title="plot.seed ? plotStageInfo(plot).tooltip : ''" @click="plotAction(land, plot)">
                <template v-if="plot.locked">🔒<br><small>未解锁</small></template>
                <template v-else-if="plot.buyable">➕<br><small>购买 {{ plot.cost }}</small></template>
                <template v-else-if="plot.seed">
                  <span v-if="showGrowMask(plot)" class="plot-grow-mask" :style="plotGrowMaskStyle(plot)">
                    <svg class="plot-wave-svg plot-wave-svg--back" viewBox="0 0 200 24" preserveAspectRatio="none" aria-hidden="true">
                      <path d="M0 9 Q12.5 0 25 9 T50 9 T75 9 T100 9 T125 9 T150 9 T175 9 T200 9 V24 H0 Z" />
                    </svg>
                    <svg class="plot-wave-svg plot-wave-svg--front" viewBox="0 0 200 24" preserveAspectRatio="none" aria-hidden="true">
                      <path d="M0 10 Q12.5 0 25 10 T50 10 T75 10 T100 10 T125 10 T150 10 T175 10 T200 10 V24 H0 Z" />
                    </svg>
                  </span>
                  <img v-if="getStageImg(plot)" :src="getStageImg(plot)" class="stage-img" :alt="plot.seed.name"><span v-else class="plot-icon">{{ plot.seed.icon }}</span><br>
                  <small>{{ plot.seed.name }}</small><br>
                  <small>{{ isPlotReady(plot) ? '可收获' : `成长中 ${formatRemain(plot)}` }}</small>
                </template>
                <template v-else>空地<br><small>点击种植</small></template>
              </button>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <v-row dense class="mb-3">
        <v-col cols="12" md="6">
          <v-card flat class="siqi-card h-100">
            <v-card-title class="siqi-card-title siqi-card-title--inventory d-flex align-center">
              收获背包
              <v-spacer />
              <v-btn color="orange" size="small" class="inventory-sell-all-btn quick-action-btn quick-action-btn--harvest" :disabled="!(farm.inventory || []).length" :loading="loading" @click="sellAll">一键出售</v-btn>
            </v-card-title>
            <v-card-text class="inventory-body">
              <div v-if="!(farm.inventory || []).length" class="inventory-empty">
                <div class="inventory-empty-icon">🎒</div>
                <div>背包空空如也</div>
                <small>成熟作物收获后会进入这里</small>
              </div>
              <div v-else class="inventory-grid">
                <div v-for="item in farm.inventory" :key="item.seed_id" class="inventory-item">
                  <div class="inventory-icon">{{ item.icon || '🌱' }}</div>
                  <div class="inventory-main">
                    <div class="inventory-name">{{ item.name || `作物 ${item.seed_id}` }}</div>
                    <div class="inventory-meta">
                      <span>数量 {{ Number(item.quantity || 0) }}</span>
                      <span>售：{{ inventoryUnitReward(item) }} 魔力/份</span>
                      <span class="inventory-bonus">含装饰加成 <b>+{{ formatPercentValue(inventoryDecorBonus()) }}%</b></span>
                    </div>
                  </div>
                  <v-btn size="small" color="orange" class="inventory-sell-btn quick-action-btn quick-action-btn--harvest" @click="sell(item)">出售</v-btn>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card flat class="siqi-card h-100">
            <v-card-title class="siqi-card-title siqi-card-title--logs">操作记录</v-card-title>
            <v-card-text class="history-body">
              <div v-if="!(farm.user_logs || []).length" class="text-grey text-center py-6">暂无操作记录</div>
              <div v-else class="history-list">
                <div v-for="log in farm.user_logs || []" :key="log.id || `${log.created_at}-${log.action}-${log.plot_index}`" class="history-item">
                  <div class="history-left">
                    <span class="history-action" :class="logMeta(log).actionClass">{{ logMeta(log).actionText }}</span>
                    <span class="history-detail">{{ logMeta(log).detailText }}</span>
                  </div>
                  <div class="history-right">
                    <span class="history-value" :class="logMeta(log).valueClass">{{ logMeta(log).valueText }}</span>
                    <span class="history-time">{{ formatLogTime(log.created_at) }}</span>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      </template>

      <!-- 参观结果展示 - 二级拟态弹窗 -->
      <v-dialog v-model="showVisitDialog" max-width="760" scrollable>
        <v-card class="neu-visit-dialog" flat>
          <v-card-title class="neu-visit-header">
            <div class="neu-visit-avatar visit-avatar">🚜</div>
            <div class="neu-visit-info">
              <div class="neu-visit-name">
                农场参观 · {{ visitTargetName() }}
                <v-chip v-if="visitedFarm.ready_count" size="x-small" color="orange" class="ml-2" variant="flat">
                  成熟 {{ visitedFarm.ready_count }}
                </v-chip>
              </div>
              <div class="neu-visit-decor">正在查看 {{ visitTargetName() }} 的农场，成熟作物 {{ Number(visitedFarm.ready_count || 0) }} 个</div>
            </div>
            <div class="neu-visit-actions">
              <v-btn color="green" variant="flat" size="small" class="visit-like-btn" @click="likeFarm(visitedFarm.target_id)" :disabled="!canLikeVisitedFarm()">
                👍 觉得农庄好看
              </v-btn>
              <v-btn icon variant="text" size="small" @click="showVisitDialog = false">
                <v-icon icon="mdi-close" color="grey" />
              </v-btn>
            </div>
          </v-card-title>
          <v-card-text style="max-height:60vh;">
            <div class="visit-like-status">{{ visitLikeStatusText() }}</div>
            <div v-if="visitedFarm.decor_counts" class="visit-decor-counts">
              <span v-for="item in visitDecorCounts()" :key="item.type" class="visit-decor-chip">{{ item.label }} {{ item.owned }}/{{ item.total }}</span>
            </div>
            <div v-if="!(visitedFarm.lands || []).length" class="neu-visit-empty">该用户暂无已解锁菜地</div>
            <div v-for="land in visitedFarm.lands || []" :key="'vl-'+land.id" class="neu-land-section">
              <div class="neu-land-title">{{ land.name }} <span class="text-caption text-grey">坑位：{{ land.effective_plot_count || land.plot_count || 0 }}</span></div>
              <div v-if="land.unlocked !== undefined && !Number(land.unlocked)" class="visit-land-locked">未解锁</div>
              <div v-else class="neu-plot-grid">
                <div v-for="plot in visitPlotsForLand(land)" :key="'vp-'+land.id+'-'+plot.plot_index" class="neu-visit-plot" :class="{ planted: !!plot.seed_id, ready: isVisitReady(plot) }">
                  <template v-if="plot.seed_id">
                    <div class="neu-plot-icon-wrap">
                      <img v-if="getVisitStageImg(plot)" :src="getVisitStageImg(plot)" class="stage-img-sm" :alt="plot.seed_name || ''">
                      <span v-else class="neu-plot-emoji">{{ plot.seed_icon || seedById(plot.seed_id)?.icon || '' }}</span>
                    </div>
                    <div class="neu-plot-label">{{ plot.seed_name || seedById(plot.seed_id)?.name || '' }}</div>
                    <div v-if="isVisitReady(plot)" class="neu-plot-badge ready">成熟</div>
                  </template>
                  <template v-else>
                    <div class="neu-plot-empty-icon">🌱</div>
                    <div class="neu-plot-label text-grey">空地</div>
                  </template>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref, resolveComponent, watch } from 'vue'

const props = defineProps({ api: Object, initialConfig: { type: Object, default: () => ({}) } })
defineEmits(['switch', 'close'])
const PLUGIN_ID = 'SiqiFram'
const loading = ref(false)
const loadingOCR = ref(false)
const farm = ref({})
const selectedSeed = ref(String(props.initialConfig.seed_id || '1'))
watch(() => props.initialConfig.seed_id, (seedId) => {
  selectedSeed.value = String(seedId || '1')
})
const message = ref('')
const messageType = ref('success')
let messageTimer = null
const summary = computed(() => farm.value.summary || {})
const initialLoading = computed(() => loading.value && !(farm.value?.lands || []).length && !(farm.value?.seeds || []).length)
const stageImageCache = reactive({})
const visiting = ref(false)
const visitUsername = ref('')
const visitedFarm = ref(null)
const showVisitDialog = ref(false)
const showStealDialog = ref(false)
const stealLoading = ref(false)
const stealTarget = ref({})
const stolenCount = ref(0)
const stolenReward = ref(0)
const stolenPlots = ref([])
const showLikeDialog = ref(false)
const showSellConfirmDialog = ref(false)
const showBuyPlotConfirmDialog = ref(false)
const pendingBuyPlot = ref(null)
const likeLoading = ref(false)
const likeUsernames = ref('')
const likeMax = ref(0)
const likeRemaining = ref(null)
const likeNextIn = ref(null)
const likeLikedList = ref([])
const apiGet = (path) => props.api.get(`/plugin/${PLUGIN_ID}${path}`)
const apiPost = (path, data = {}) => props.api.post(`/plugin/${PLUGIN_ID}${path}`, data)
const STAGE_LABELS = { seedling: '幼芽期', growth: '生长期', mature: '成熟期' }
const defaultStagePhaseConfig = { seedling_ratio: 0.5, growth_ratio: 0.5 }
const statColorMap = {
  orange: '#f59e0b',
  green: '#10b981',
  red: '#ef4444',
  blue: '#3b82f6'
}
const sellAllItems = computed(() => (farm.value.inventory || []).filter(item => Number(item.quantity || 0) > 0))
const sellAllSummary = computed(() => sellAllItems.value.reduce((summary, item) => {
  const quantity = Number(item.quantity || 0)
  summary.totalQuantity += quantity
  summary.totalReward += quantity * inventoryUnitReward(item)
  return summary
}, { totalQuantity: 0, totalReward: 0 }))

const StatCard = (props) => {
  const VIcon = resolveComponent('VIcon')
  const color = statColorMap[props.color] || 'rgba(var(--v-theme-on-surface),.78)'
  return h('div', { class: `stat-card stat-${props.color}` }, [
    h('div', { class: `stat-icon stat-icon-${props.color}`, style: { color, background: 'transparent' } }, [h(VIcon, { icon: props.icon, size: 22, color })]),
    h('div', { class: 'stat-content' }, [
      h('div', { class: 'stat-title', style: { color } }, props.title),
      h('div', { class: 'stat-value', style: { color } }, String(props.value))
    ])
  ])
}

function show(text, type = 'success') {
  message.value = text
  messageType.value = type
  if (messageTimer) clearTimeout(messageTimer)
  messageTimer = setTimeout(() => {
    if (message.value === text) message.value = ''
    messageTimer = null
  }, 3000)
}
async function loadFarmData({ force = false, notify = false } = {}) {
  loading.value = true
  try {
    const res = force ? await apiPost('/refresh') : await apiGet('/data')
    if (res.success) {
      farm.value = res
      if (!visitUsername.value.trim()) visitUsername.value = res.current_username || res.username || res.user_name || ''
      prefetchStageImages()
      if (notify) show('刷新完成')
    } else {
      show(res.message || res.msg || (force ? '刷新失败' : '暂无缓存数据，请点击刷新'), 'error')
    }
  } catch (e) { show(`${force ? '刷新' : '加载'}失败：${e.message}`, 'error') } finally { loading.value = false }
}

async function loadDefaultSeed() {
  try {
    const config = await apiGet('/config')
    if (config?.seed_id !== undefined) selectedSeed.value = String(config.seed_id || '1')
  } catch (e) {
    console.warn('加载默认种子失败', e)
  }
}

function refresh(notify = false) {
  return loadFarmData({ force: true, notify })
}
function formatSeconds(seconds) {
  const s = Number(seconds || 0)
  if (s >= 86400) return `${Math.round(s / 86400)}天`
  if (s >= 3600) return `${Math.round(s / 3600)}小时`
  return `${Math.round(s / 60)}分钟`
}
function formatHms(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds || 0)))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${h}小时${m}分钟${s}秒`
}
function formatPercentValue(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  if (Math.abs(num - Math.round(num)) < 1e-9) return String(Math.round(num))
  return String(num.toFixed(2)).replace(/\.?0+$/, '')
}
function inventoryDecorBonus() {
  return Number(farm.value?.decorations?.sell_bonus_percent_total || 0)
}
function inventoryBaseUnitReward(item) {
  const seed = seedById(item?.seed_id)
  const fallback = seed ? Math.round(Number(seed.base_reward || 0) * Number(seed.bonus || 1)) : 0
  return Number(item?.base_unit_reward || item?.unit_reward || fallback || 0)
}
function inventoryUnitReward(item) {
  const base = inventoryBaseUnitReward(item)
  return Math.round(base * (100 + inventoryDecorBonus()) / 100)
}
function isSeedUnlocked(seed) { return Number(farm.value.user_stats?.total_harvest || 0) >= Number(seed.unlock_harvest || 0) }
function selectSeed(seed) { if (isSeedUnlocked(seed)) selectedSeed.value = String(seed.id); else show('种子未解锁', 'error') }
function landUnlocked(land) { return Number(farm.value.user_stats?.total_harvest || 0) >= Number(land.unlock_harvest || 0) }
function seedById(id) { return (farm.value.seeds || []).find(s => Number(s.id) === Number(id)) }
function landPlotCountLabel(land) {
  const plotSlot = farm.value.plot_slot || {}
  const enabled = !!plotSlot.enabled
  const landId = Number(land.id)
  const maxPerLand = Number(plotSlot.max_per_land || 0) || Number(land.plot_count || 0)
  const effectiveCounts = plotSlot.effective_plot_counts || {}
  const effective = enabled && effectiveCounts && typeof effectiveCounts === 'object' && Object.prototype.hasOwnProperty.call(effectiveCounts, landId)
    ? Number(effectiveCounts[landId] || land.plot_count || 0)
    : Number(land.plot_count || 0)
  return enabled ? `${effective}/${maxPerLand}` : `${Number(land.plot_count || 0)}`
}
function plotsForLand(land) {
  const effective = Number(farm.value.plot_slot?.effective_plot_counts?.[land.id] || land.plot_count || 0)
  const max = Number(farm.value.plot_slot?.max_per_land || effective)
  const nextCost = farm.value.plot_slot?.next_slot_cost_by_land?.[land.id]
  const rows = []
  const userPlots = farm.value.user_lands || []
  for (let i = 0; i < Math.max(max, effective); i++) {
    const raw = userPlots.find(p => Number(p.land_id) === Number(land.id) && Number(p.plot_index) === i)
    if (!landUnlocked(land)) rows.push({ plot_index: i, locked: true })
    else if (i >= effective) rows.push(i === effective && nextCost ? { plot_index: i, buyable: true, cost: nextCost } : { plot_index: i, locked: true })
    else rows.push({ ...(raw || { land_id: land.id, plot_index: i }), seed: raw?.seed_id ? seedById(raw.seed_id) : null })
  }
  return rows
}
function nowSec() { return Math.floor(Date.now() / 1000) }
function isPlotReady(plot) {
  if (!plot || !plot.seed) return false
  const harvestTime = Number(plot.harvest_time || 0)
  return Number(plot.is_ready || 0) === 1 || (harvestTime > 0 && harvestTime <= nowSec())
}
function formatRemain(plot) {
  const remain = Math.max(0, Number(plot.harvest_time || 0) - nowSec())
  if (!remain) return ''
  if (remain >= 86400) return `${Math.floor(remain / 86400)}天${Math.floor((remain % 86400) / 3600)}小时`
  if (remain >= 3600) return `${Math.floor(remain / 3600)}小时${Math.floor((remain % 3600) / 60)}分`
  if (remain >= 60) return `${Math.floor(remain / 60)}分`
  return `${remain}秒`
}
function stagePhaseConfig() {
  return farm.value.stage_phase_config || defaultStagePhaseConfig
}
function plotProgress(plot) {
  if (!plot || !plot.seed) return 0
  if (isPlotReady(plot)) return 100
  const total = Number(plot.seed.grow_time || 0)
  const plantTime = Number(plot.plant_time || 0)
  if (total <= 0 || plantTime <= 0) return 0
  return Math.max(0, Math.min(100, ((nowSec() - plantTime) / total) * 100))
}
function plotStageInfo(plot) {
  const seed = plot.seed
  const icons = seed && seed.stage_icons
  const cfg = stagePhaseConfig()
  const seedlingRatio = Math.max(0, Number(cfg.seedling_ratio ?? 0.5))
  const growthRatio = Math.max(0, Number(cfg.growth_ratio ?? 0.5))
  const progress = plotProgress(plot) / 100
  let phase = 'growth'
  if (isPlotReady(plot)) {
    phase = 'mature'
  } else if (progress < seedlingRatio) {
    phase = 'seedling'
  } else if (progress < seedlingRatio + growthRatio) {
    phase = 'growth'
  }
  const phasePath = icons ? (icons[phase] || icons.mature || icons.growth || icons.seedling || null) : null
  const label = STAGE_LABELS[phase] || ''
  const seedName = seed?.name || ''
  return {
    phase,
    label,
    tooltip: seedName ? `${seedName}（${label}）` : label,
    src: phasePath ? (stageImageCache[phasePath] || null) : null,
    progress: plotProgress(plot)
  }
}
function getStageImg(plot) {
  return plotStageInfo(plot).src
}
function plotGrowMaskStyle(plot) {
  return { height: `${plotProgress(plot).toFixed(1)}%` }
}
function showGrowMask(plot) {
  return !isPlotReady(plot) && plotProgress(plot) < 99.5
}
async function prefetchStageImages() {
  const seeds = farm.value.seeds || []
  const paths = new Set()
  for (const seed of seeds) {
    const icons = seed.stage_icons
    if (!icons) continue
    if (icons.seedling) paths.add(icons.seedling)
    if (icons.growth) paths.add(icons.growth)
    if (icons.mature) paths.add(icons.mature)
  }
  for (const p of paths) {
    if (stageImageCache[p]) continue
    try {
      const res = await apiGet(`/stage-image?path=${encodeURIComponent(p)}`)
      if (res && res.success && res.data) {
        stageImageCache[p] = res.data
      }
    } catch (e) { /* ignore */ }
  }
}
function plotClass(plot) { return { locked: plot.locked, buyable: plot.buyable, ready: isPlotReady(plot), planted: !!plot.seed } }
async function plotAction(land, plot) {
  if (plot.locked) return
  if (plot.buyable) return buyPlotSlot(land, plot)
  if (plot.seed) return isPlotReady(plot) ? harvest(land.id, plot.plot_index) : show('作物尚未成熟', 'info')
  if (!selectedSeed.value) return show('请先选择种子', 'error')
  const res = await apiPost('/plant', { land_id: land.id, plot_index: plot.plot_index, seed_id: selectedSeed.value })
  show(res.msg || res.message || (res.success ? '种植成功' : '种植失败'), res.success ? 'success' : 'error')
  refresh()
}
async function buyPlotSlot(land, plot) {
  pendingBuyPlot.value = { land, plot }
  showBuyPlotConfirmDialog.value = true
}
async function confirmBuyPlotSlot() {
  const pending = pendingBuyPlot.value
  if (!pending?.land) return show('缺少购买坑位信息', 'error')
  loading.value = true
  try {
    const res = await apiPost('/buy-plot-slot', { land_id: pending.land.id })
    show(res.msg || res.message || (res.success ? '购买成功' : '购买失败'), res.success ? 'success' : 'error')
    if (res.success) {
      showBuyPlotConfirmDialog.value = false
      pendingBuyPlot.value = null
    }
    refresh()
  } catch (e) {
    show(`购买失败：${e.message}`, 'error')
  } finally { loading.value = false }
}
async function harvest(landId, plotIndex) { const res = await apiPost('/harvest', { land_id: landId, plot_index: plotIndex }); show(res.msg || res.message || '已请求收获', res.success ? 'success' : 'error'); refresh() }
async function plantFill() { const res = await apiPost('/plant-fill', { seed_id: selectedSeed.value }); show(res.msg || res.message || '已请求种植', res.success ? 'success' : 'error'); refresh() }
async function harvestAllOCR() {
  loadingOCR.value = true
  try {
    const res = await apiPost('/harvest-ocr')
    show(res.message || (res.success ? '收获成功' : '收获失败'), res.success ? 'success' : 'error')
  } catch (e) {
    show('收获请求异常', 'error')
  } finally {
    loadingOCR.value = false
    refresh()
  }
}
async function sell(item) { const res = await apiPost('/sell', { seed_id: item.seed_id, quantity: item.quantity }); show(res.msg || res.message || '已请求出售', res.success ? 'success' : 'error'); refresh() }
function sellAll() {
  if (!sellAllItems.value.length) return show('背包暂无可出售库存', 'info')
  showSellConfirmDialog.value = true
}
async function confirmSellAll() {
  const items = [...sellAllItems.value]
  if (!items.length) return show('背包暂无可出售库存', 'info')
  loading.value = true
  try {
    let success = 0
    let lastMessage = ''
    for (const item of items) {
      const res = await apiPost('/sell', { seed_id: item.seed_id, quantity: item.quantity })
      if (res.success) success += 1
      lastMessage = res.msg || res.message || lastMessage
    }
    show(success ? `已尝试出售 ${success} 类库存` : (lastMessage || '出售失败'), success ? 'success' : 'error')
    showSellConfirmDialog.value = false
    refresh()
  } catch (e) {
    show(`出售失败：${e.message}`, 'error')
  } finally { loading.value = false }
}
async function steal() {
  if (!farm.value.can_steal) return show('今日已偷过菜，明天再来吧', 'error')
  stealLoading.value = true
  try {
    const res = await apiPost('/steal-target')
    if (res.success) {
      stealTarget.value = res
      stolenCount.value = 0
      stolenReward.value = 0
      stolenPlots.value = []
      showStealDialog.value = true
      show('已找到偷菜目标', 'success')
    } else {
      show(res.msg || res.message || '偷菜目标获取失败', 'error')
    }
  } catch (e) { show(`偷菜目标获取失败：${e.message}`, 'error') } finally { stealLoading.value = false }
}
function stealPlotsForLand(land) {
  const count = Number(land.effective_plot_count || land.plot_count || 0)
  const plots = stealTarget.value.victim_plots || []
  const rows = []
  for (let i = 0; i < count; i++) {
    rows.push(plots.find(p => Number(p.land_id) === Number(land.id) && Number(p.plot_index) === i) || { land_id: land.id, plot_index: i })
  }
  return rows
}
function isStealablePlot(plot) { return !!plot?.seed_id && (Number(plot.is_ready || 0) === 1 || (plot.harvest_time && Number(plot.harvest_time) <= nowSec())) }
function stealPlotClass(plot) { return { planted: !!plot.seed_id, ready: isStealablePlot(plot), stealable: isStealablePlot(plot) && !plot.stolen, stolen: !!plot.stolen } }
function getStealStageImg(plot) {
  const seed = seedById(plot.seed_id)
  const icons = plot.stage_icons || seed?.stage_icons
  if (!icons) return null
  if (isStealablePlot(plot)) return stageImageCache[icons.mature] || stageImageCache[icons.growth] || null
  return stageImageCache[icons.growth] || stageImageCache[icons.seedling] || null
}
async function stealPlotAction(land, plot) {
  const max = Number(stealTarget.value.max_steal_count || 0)
  const already = Number(stealTarget.value.steal_count_today || 0) + stolenCount.value
  if (already >= max) return show('已达到最大偷取数量', 'error')
  if (!isStealablePlot(plot) || plot.stolen) return
  stealLoading.value = true
  try {
    const res = await apiPost('/steal-plot', { victim_id: stealTarget.value.victim_id, land_id: land.id, plot_index: plot.plot_index })
    if (res.success) {
      plot.stolen = true
      stolenCount.value += 1
      stolenReward.value += Number(res.reward || 0)
      if (res.plot_info) stolenPlots.value.push(res.plot_info)
      show(res.msg || `偷菜成功，获得 ${res.reward || 0} 魔力`, 'success')
      if (Number(stealTarget.value.steal_count_today || 0) + stolenCount.value >= max) await finishStealing()
    } else {
      show(res.msg || res.message || '偷菜失败', 'error')
    }
  } catch (e) { show(`偷菜失败：${e.message}`, 'error') } finally { stealLoading.value = false }
}
async function finishStealing() {
  if (!stolenCount.value) return show('请先选择要偷的作物', 'error')
  stealLoading.value = true
  try {
    const res = await apiPost('/steal-finish')
    show(res.msg || res.message || `偷菜完成，共获得 ${stolenReward.value} 魔力`, res.success ? 'success' : 'error')
    if (res.success) {
      closeStealDialog()
      refresh()
    }
  } catch (e) { show(`完成偷菜失败：${e.message}`, 'error') } finally { stealLoading.value = false }
}
function closeStealDialog() { showStealDialog.value = false }
async function likeRandom() { const res = await apiPost('/like-random'); show(res.msg || res.message || (res.success ? '点赞完成' : '点赞失败'), res.success ? 'success' : 'error'); refresh() }
async function openLikeDialog() {
  showLikeDialog.value = true
  if (!likeUsernames.value.trim()) await loadLikeTargets()
}
async function loadLikeTargets() {
  likeLoading.value = true
  try {
    const res = await apiPost('/like-targets')
    if (res.success) {
      likeMax.value = Number(res.max_per_window || 0)
      likeRemaining.value = Number(res.remaining_in_window ?? 0)
      likeNextIn.value = Number(res.next_available_in ?? 0)
      likeLikedList.value = Array.isArray(res.liked_list) ? res.liked_list : []
      likeUsernames.value = (Array.isArray(res.usernames) ? res.usernames : []).join('\n')
      show('点赞名单已填充', 'success')
    } else {
      show(res.msg || res.message || '随机填充失败', 'error')
    }
  } catch (e) { show(`随机填充失败：${e.message}`, 'error') } finally { likeLoading.value = false }
}
async function submitLikeBatch() {
  const raw = likeUsernames.value.trim()
  if (!raw) return show('请先填写用户名', 'error')
  likeLoading.value = true
  try {
    const res = await apiPost('/like-random', { usernames: raw })
    if (res.success) {
      show(res.msg || '一键点赞成功', 'success')
      likeRemaining.value = Number(res.remaining_in_window ?? likeRemaining.value ?? 0)
      likeNextIn.value = Number(res.next_available_in ?? likeNextIn.value ?? 0)
      if (Array.isArray(res.liked_list)) likeLikedList.value = res.liked_list
      refresh()
    } else {
      show(res.msg || res.message || '一键点赞失败', 'error')
      if (typeof res.remaining_in_window === 'number') likeRemaining.value = Number(res.remaining_in_window)
      if (typeof res.next_available_in === 'number') likeNextIn.value = Number(res.next_available_in)
      if (Array.isArray(res.liked_list)) likeLikedList.value = res.liked_list
    }
  } catch (e) { show(`一键点赞失败：${e.message}`, 'error') } finally { likeLoading.value = false }
}
async function likeFarm(targetId) { const res = await apiPost('/like-farm', { target_id: targetId }); show(res.msg || res.message || (res.success ? '点赞成功' : '点赞失败'), res.success ? 'success' : 'error') }
async function visitFarm() {
  visiting.value = true
  try {
    const res = await apiPost('/visit-farm', { username: visitUsername.value.trim() })
    if (res.success) { visitedFarm.value = res; showVisitDialog.value = true; show('访问成功', 'success') }
    else show(res.msg || res.message || '访问失败', 'error')
  } catch (e) { show(`访问失败：${e.message}`, 'error') } finally { visiting.value = false }
}
async function visitRandom() {
  visiting.value = true
  try {
    const res = await apiPost('/visit-random')
    if (res.success) { visitedFarm.value = res; showVisitDialog.value = true; show('访问成功', 'success') }
    else show(res.msg || res.message || '访问失败', 'error')
  } catch (e) { show(`访问失败：${e.message}`, 'error') } finally { visiting.value = false }
}
function visitTargetName() { return visitedFarm.value?.target_desc_name || visitedFarm.value?.target_name || visitedFarm.value?.target_username || visitedFarm.value?.username || visitedFarm.value?.user_name || visitUsername.value || '未知用户' }
function visitPlotsForLand(land) {
  const count = Number(land.effective_plot_count || land.plot_count || 0)
  const source = Array.isArray(land.plots) ? land.plots : Array.isArray(visitedFarm.value?.plots) ? visitedFarm.value.plots : []
  const rows = []
  for (let i = 0; i < count; i++) {
    rows.push(source.find(p => Number(p.land_id ?? land.id) === Number(land.id) && Number(p.plot_index) === i) || { land_id: land.id, plot_index: i })
  }
  return rows
}
function canLikeVisitedFarm() {
  const targetId = Number(visitedFarm.value?.target_id || 0)
  const selfId = Number(farm.value.uid || 0)
  const remaining = visitedFarm.value?.like_status?.remaining
  if (!targetId || (selfId > 0 && targetId === selfId)) return false
  return !(typeof remaining === 'number' && remaining <= 0)
}
function visitLikeStatusText() {
  const targetId = Number(visitedFarm.value?.target_id || 0)
  const selfId = Number(farm.value.uid || 0)
  const meta = visitedFarm.value?.like_status || {}
  const remaining = typeof meta.remaining === 'number' ? Number(meta.remaining) : null
  const nextIn = typeof meta.next_available_in === 'number' ? Number(meta.next_available_in) : 0
  const likedName = visitedFarm.value?.liked_today?.to_username || ''
  const parts = []
  if (selfId > 0 && targetId > 0 && selfId === targetId) parts.push('不能给自己的农庄点赞')
  else {
    if (likedName) parts.push(`今日已为 ${likedName} 点赞`)
    parts.push(remaining === null ? '每天可点赞一次（对任意农庄共用次数）' : `剩余：${remaining} 次`)
    if (nextIn > 0) parts.push(`下次可用：${formatHms(nextIn)}`)
  }
  return parts.filter(Boolean).join(' | ')
}
function visitDecorCounts() {
  const counts = visitedFarm.value?.decor_counts || {}
  const map = { stead: '农庄', farm: '农场', plot: '坑位', progress: '进度条' }
  return Object.keys(map).map(type => ({ type, label: map[type], owned: Number(counts[type]?.owned || 0), total: Number(counts[type]?.total || 0) }))
}
function isVisitReady(plot) { return Number(plot.is_ready || 0) === 1 || (plot.harvest_time && Number(plot.harvest_time) <= nowSec()) }
function getVisitStageImg(plot) {
  const icons = plot.stage_icons
  if (!icons) return null
  if (isVisitReady(plot)) return stageImageCache[icons.mature] || stageImageCache[icons.growth] || null
  const total = Number(plot.grow_time || 0)
  const plantTime = Number(plot.plant_time || 0)
  if (total > 0 && plantTime > 0) {
    const progress = Math.max(0, Math.min(1, (nowSec() - plantTime) / total))
    return progress < 0.5 ? (stageImageCache[icons.seedling] || stageImageCache[icons.growth] || null) : (stageImageCache[icons.growth] || null)
  }
  return stageImageCache[icons.growth] || null
}
function logUnit(action, likelySell) {
  if (action === 'harvest') return '收获值'
  if (likelySell || ['plant', 'sell', 'steal', 'stolen', 'buy_slot', 'buy_decor'].includes(action)) return '魔力值'
  return ''
}
function logMeta(log) {
  const action = String(log?.action || '').trim()
  const likelySell = action === 'sell' || (!action && Number(log?.land_id || 0) === 0 && Number(log?.plot_index || 0) === 0 && Number(log?.value || 0) > 0 && Number(log?.seed_id || 0) > 0)
  const actionMap = { plant: ['种植', 'plant'], harvest: ['收获', 'harvest'], steal: ['偷菜', 'steal'], stolen: ['被偷', 'stolen'], buy_slot: ['购买坑位', 'plant'], buy_decor: ['购买装饰', 'plant'] }
  const mapped = likelySell ? ['售出', 'sell'] : (actionMap[action] || [action || '未知', ''])
  const parts = [log?.seed_icon, log?.seed_name].filter(Boolean)
  const hasPlotIndex = log?.plot_index !== undefined && log?.plot_index !== null && !Number.isNaN(Number(log.plot_index))
  if (log?.land_name) parts.push(`(${log.land_name}${hasPlotIndex ? `-${Number(log.plot_index) + 1}号地` : ''})`)
  if (log?.extra) parts.push(String(log.extra))
  if (likelySell && Number(log?.quantity || 0) > 0) parts.push(`数量：${Number(log.quantity)}`)
  const unit = logUnit(action, likelySell)
  const value = Number(log?.value || 0)
  return {
    actionText: mapped[0],
    actionClass: `history-action--${mapped[1]}`,
    detailText: parts.join(' ') || '-',
    valueText: `${value > 0 ? '+' : ''}${value}${unit ? ` ${unit}` : ''}`,
    valueClass: value > 0 ? 'history-value--plus' : 'history-value--minus'
  }
}
function formatLogTime(time) {
  if (!time) return ''
  const date = new Date(String(time).includes('T') ? time : String(time).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return String(time)
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadDefaultSeed()
  loadFarmData()
})
</script>

<style scoped>
.siqi-page{padding:16px 20px;display:flex;flex-direction:column;gap:16px;min-height:400px;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Inter',sans-serif;color:rgba(var(--v-theme-on-surface),.85);border:1px solid rgba(var(--v-theme-on-surface),.12);border-radius:8px;background:linear-gradient(180deg,rgba(255,255,255,.02),rgba(76,175,80,.025))}
.siqi-page :deep(.v-btn){transition:transform .16s ease,box-shadow .16s ease,filter .16s ease,opacity .16s ease}.siqi-page :deep(.v-btn:not(.v-btn--disabled):hover){transform:translateY(-1px);box-shadow:0 6px 16px rgba(15,23,42,.12);filter:saturate(1.05)}.siqi-page :deep(.v-btn:not(.v-btn--disabled):active){transform:translateY(0) scale(.98);box-shadow:0 2px 8px rgba(15,23,42,.10)}.siqi-page :deep(.v-btn.v-btn--disabled){cursor:not-allowed;opacity:.55}
.siqi-page button,.seed,.plot,.neu-action-card,.visit-btn{transition:transform .16s ease,box-shadow .16s ease,filter .16s ease,opacity .16s ease}.siqi-page button:not(:disabled):active,.seed:not(.locked):active,.plot:not(.locked):active,.neu-action-card:active,.visit-btn:not(:disabled):active{transform:translateY(0) scale(.97)!important;box-shadow:0 2px 8px rgba(15,23,42,.10)!important;filter:saturate(1.08)}.siqi-page button:disabled{cursor:not-allowed;opacity:.55}.seed:focus-visible,.plot:focus-visible,.siqi-page button:focus-visible{outline:2px solid rgba(76,175,80,.55);outline-offset:2px}
.siqi-toast{position:fixed!important;top:18px!important;left:50%!important;transform:translateX(-50%)!important;z-index:99999!important;width:min(520px,calc(100vw - 32px))!important;margin:0!important;box-shadow:0 12px 36px rgba(15,23,42,.18)!important;border-radius:12px!important}
.page-skeleton{display:flex;flex-direction:column;gap:0}.skeleton-shell{pointer-events:none}.skeleton-stat{min-height:78px}.skeleton-actions{display:flex;flex-direction:column;gap:8px;width:100%}.sk{position:relative;overflow:hidden;border-radius:10px;background:rgba(var(--v-theme-on-surface),.075);border:1px solid rgba(var(--v-theme-on-surface),.035)}.sk::after{content:"";position:absolute;inset:0;transform:translateX(-100%);background:linear-gradient(90deg,transparent,rgba(var(--v-theme-surface),.46),transparent);animation:skeleton-shimmer 1.25s infinite}.sk-icon{width:38px;height:38px;border-radius:12px;flex:0 0 38px}.sk-lines{flex:1}.sk-line{height:18px;margin-top:7px}.sk-line.short{width:58%;height:12px;margin-top:0}.sk-title{width:128px;height:16px}.sk-button{width:76px;height:28px;border-radius:4px}.sk-seed{height:46px;border-radius:11px}.sk-action{height:46px;border-radius:11px}.sk-plot{height:78px;border-radius:12px}.sk-row{height:34px;margin-top:10px;border-radius:10px}@keyframes skeleton-shimmer{100%{transform:translateX(100%)}}@keyframes plot-wave-slide{100%{transform:translateX(-50%)}}
.siqi-topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-bottom:8px}.siqi-topbar__left{display:flex;align-items:center;gap:12px;min-width:0;flex:1}.siqi-topbar__right{display:flex;align-items:center;gap:10px;flex-shrink:0}.siqi-topbar__right :deep(.v-btn-group){flex-wrap:nowrap}.siqi-topbar__icon{width:42px;height:42px;border-radius:11px;background:rgba(76,175,80,.14);display:flex;align-items:center;justify-content:center;color:#2e7d32;flex-shrink:0}.siqi-topbar__title{font-size:16px;font-weight:700;letter-spacing:-.3px;color:rgba(var(--v-theme-on-surface),.88)}.siqi-topbar__sub{font-size:11px;color:rgba(var(--v-theme-on-surface),.55);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.siqi-content{display:flex;flex-direction:column;gap:0}
.siqi-card{background:rgba(var(--v-theme-on-surface),.03)!important;backdrop-filter:blur(20px) saturate(150%);border-radius:14px!important;border:.5px solid rgba(var(--v-theme-on-surface),.08)!important;box-shadow:0 2px 10px rgba(0,0,0,.05)!important;overflow:hidden}.siqi-card-title{min-height:44px;padding:10px 16px!important;font-size:13px!important;font-weight:700!important;background:rgba(76,175,80,.08);border-bottom:.5px solid rgba(var(--v-theme-on-surface),.07);color:rgba(var(--v-theme-on-surface),.84)}.siqi-card-title--farm{background:rgba(121,85,72,.08)}.siqi-card-title--inventory{background:rgba(251,146,60,.10)}.siqi-card-title--logs{background:rgba(59,130,246,.09)}
.seed-interact-row{display:grid;grid-template-columns:minmax(520px,1fr) minmax(360px,1fr);gap:12px;align-items:stretch}.seed-shop-card{width:100%;min-width:0;display:flex;flex-direction:column}.seed-interact-row>.siqi-card{height:100%}.seed-shop-body{flex:1;display:flex;align-items:center;padding:16px!important}.seed-grid{width:100%;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.seed{position:relative;display:flex;align-items:center;gap:7px;min-height:46px;border:1px solid rgba(76,175,80,.16);background:rgba(var(--v-theme-surface),.88);border-radius:11px;padding:7px 8px;cursor:pointer;text-align:left;font-size:12px;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}.seed:hover{transform:translateY(-1px);box-shadow:0 6px 14px rgba(15,23,42,.07)}.seed.selected{border-color:#43a047;background:#e8f5e9;box-shadow:0 0 0 2px rgba(165,214,167,.75)}.seed.locked{opacity:.58}.seed-icon{width:28px;height:28px;display:grid;place-items:center;flex:0 0 28px;border-radius:9px;background:rgba(76,175,80,.09);font-size:20px}.seed-main{min-width:0;flex:1 1 auto}.seed-name{font-weight:800;color:rgba(var(--v-theme-on-surface),.84);line-height:1.1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.seed-meta{margin-top:3px;color:rgba(var(--v-theme-on-surface),.52);font-size:11px;line-height:1.15;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.seed-lock{flex:0 0 auto;min-width:72px;text-align:center;white-space:nowrap;padding:2px 6px;border-radius:999px;background:rgba(239,68,68,.10);color:#dc2626;font-size:10px;font-weight:800}.plot-icon{font-size:26px}.stage-img{width:40px;height:40px;image-rendering:auto;display:block;margin:0 auto}.stage-img-sm{width:28px;height:28px;image-rendering:auto;display:block;margin:0 auto}.plot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(86px,1fr));gap:10px}.plot{min-height:78px;border:1px solid #d6c2a6;background:#fff8e1;border-radius:12px;cursor:pointer;transition:transform .18s ease,box-shadow .18s ease}.plot:hover:not(.locked){transform:translateY(-1px);box-shadow:0 8px 18px rgba(120,72,20,.10)}.plot.planted{background:#e8f5e9;border-color:#81c784}.plot.ready{background:#fff3e0;border-color:#ff9800}.plot.locked{background:#f2f2f2;color:#999;cursor:not-allowed}.plot.buyable{background:#e3f2fd;border-color:#42a5f5}.stat-card{border-radius:14px;padding:12px 14px;border:.5px solid rgba(var(--v-theme-on-surface),.08);background:rgba(var(--v-theme-on-surface),.03);box-shadow:inset 0 1px 0 rgba(255,255,255,.2),0 2px 12px rgba(var(--v-theme-on-surface),.08)}.stat-title{font-size:11px;color:rgba(var(--v-theme-on-surface),.55);font-weight:600}.stat-value{font-size:20px;font-weight:800;letter-spacing:-.5px}.stat-orange{background:rgba(245,158,11,.12);border-color:rgba(245,158,11,.24)}.stat-green{background:rgba(16,185,129,.12);border-color:rgba(16,185,129,.24)}.stat-blue{background:rgba(59,130,246,.12);border-color:rgba(59,130,246,.24)}.stat-red{background:rgba(239,68,68,.12);border-color:rgba(239,68,68,.24)}.border{border:1px solid rgba(0,0,0,.08)}

/* 农场互动 */
.land-body{padding:16px!important}.land-section{padding:14px;margin-bottom:14px;border-radius:14px;background:rgba(var(--v-theme-surface),.72);border:1px solid rgba(var(--v-theme-on-surface),.07)}.land-section:last-child{margin-bottom:0}.land-title{font-size:13px;font-weight:800;color:rgba(var(--v-theme-on-surface),.78);margin-bottom:10px}.land-section .plot-grid{grid-template-columns:repeat(auto-fit,minmax(96px,1fr));width:100%}.land-section .plot{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0;padding:6px;line-height:1.05}.land-section .plot .stage-img{margin:0 auto}.land-section .plot br{display:none}.land-section .plot small{display:block;margin-top:2px;line-height:1.1}.stat-card{display:flex;align-items:center;gap:12px}.stat-icon{width:38px;height:38px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:rgba(var(--v-theme-surface),.72);color:rgba(var(--v-theme-on-surface),.68);flex:0 0 38px}.stat-content{min-width:0}.farm-interact-card{overflow:hidden}.farm-interact-subtitle{margin-left:10px;color:rgba(var(--v-theme-on-surface),.48);font-size:12px;font-weight:500}.farm-interact-body{padding:16px !important;background:transparent}
.farm-action-list{height:100%;margin:-4px!important}.farm-action-list>.v-col{padding:4px!important}
.land-plot-count{margin-left:4px;color:rgba(var(--v-theme-on-surface),.52);font-size:12px;font-weight:700}.land-locked-mobile-hint{display:none}

.land-section .plot{position:relative;overflow:hidden}.plot-grow-mask{position:absolute;left:0;right:0;bottom:0;z-index:0;pointer-events:none;overflow:hidden;background:transparent;transition:height .35s ease;border-radius:0 0 12px 12px}.plot-grow-mask::before{content:"";position:absolute;left:0;right:0;top:18px;bottom:0;background:rgba(76,175,80,.22)}.plot-wave-svg{position:absolute;left:0;top:0;width:200%;height:18px;display:block;animation:plot-wave-slide 3.8s linear infinite}.plot-wave-svg path{fill:rgba(76,175,80,.22)}.plot-wave-svg--back{top:0;height:18px;opacity:.16;animation-duration:5.6s;animation-direction:reverse}.plot-wave-svg--back path{fill:rgba(76,175,80,.22)}.plot-wave-svg--front{opacity:1}.land-section .plot>img,.land-section .plot>.plot-icon,.land-section .plot>small{position:relative;z-index:1}
.seed,.neu-action-card,.plot{background:rgba(var(--v-theme-surface),.86);color:rgba(var(--v-theme-on-surface),.86)}.seed.selected{background:rgba(76,175,80,.18);border-color:rgba(76,175,80,.58);box-shadow:0 0 0 2px rgba(76,175,80,.20)}.plot{background:rgba(121,85,72,.12);border-color:rgba(166,124,82,.32);color:rgba(var(--v-theme-on-surface),.84)}.plot.planted{background:rgba(76,175,80,.14);border-color:rgba(76,175,80,.30)}.plot.ready{background:rgba(255,152,0,.16);border-color:rgba(255,152,0,.42)}.plot.locked{background:rgba(var(--v-theme-on-surface),.045)!important;border-color:rgba(var(--v-theme-on-surface),.12)!important;color:rgba(var(--v-theme-on-surface),.45)!important;opacity:1}.plot.locked small{color:rgba(var(--v-theme-on-surface),.42)!important}.plot.buyable{background:rgba(33,150,243,.13);border-color:rgba(33,150,243,.34);color:#42a5f5}.plot-grow-mask{background:linear-gradient(180deg,rgba(76,175,80,.14),rgba(76,175,80,.30))}.visit-username-input :deep(.v-field){background:rgba(var(--v-theme-surface),.72)!important;color:rgba(var(--v-theme-on-surface),.86)}.visit-username-input :deep(.v-field__input){color:rgba(var(--v-theme-on-surface),.86)}.visit-username-input :deep(input::placeholder){color:rgba(var(--v-theme-on-surface),.45)}
.land-section .plot .plot-grow-mask{background:transparent}

.stat-icon-orange{color:#f59e0b;background:rgba(245,158,11,.14)}
.stat-icon-green{color:#10b981;background:rgba(16,185,129,.14)}
.stat-icon-red{color:#ef4444;background:rgba(239,68,68,.14)}
.stat-icon-blue{color:#3b82f6;background:rgba(59,130,246,.14)}
.stat-orange .stat-icon,.stat-orange .stat-title,.stat-orange .stat-value{color:#f59e0b!important}.stat-orange .stat-title{color:rgba(245,158,11,.82)!important}.stat-orange .stat-icon{background:rgba(245,158,11,.14)!important}
.stat-green .stat-icon,.stat-green .stat-title,.stat-green .stat-value{color:#10b981!important}.stat-green .stat-title{color:rgba(16,185,129,.82)!important}.stat-green .stat-icon{background:rgba(16,185,129,.14)!important}
.stat-red .stat-icon,.stat-red .stat-title,.stat-red .stat-value{color:#ef4444!important}.stat-red .stat-title{color:rgba(239,68,68,.82)!important}.stat-red .stat-icon{background:rgba(239,68,68,.14)!important}
.stat-blue .stat-icon,.stat-blue .stat-title,.stat-blue .stat-value{color:#3b82f6!important}.stat-blue .stat-title{color:rgba(59,130,246,.82)!important}.stat-blue .stat-icon{background:rgba(59,130,246,.14)!important}

.history-body{max-height:320px;overflow-y:auto;padding:12px!important}.history-list{display:flex;flex-direction:column;border-radius:12px;background:rgba(var(--v-theme-surface),.68);border:1px solid rgba(var(--v-theme-on-surface),.06);overflow:hidden}.history-item{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:12px;padding:9px 12px;border-bottom:1px solid rgba(var(--v-theme-on-surface),.07);font-size:12px}.history-item:last-child{border-bottom:none}.history-left,.history-right{display:flex;align-items:center;gap:6px;min-width:0}.history-left{justify-content:flex-start}.history-right{justify-content:flex-end;text-align:right;white-space:nowrap}.history-action,.history-value{font-weight:900;flex:0 0 auto}.history-detail{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:rgba(var(--v-theme-on-surface),.64)}.history-time{color:rgba(var(--v-theme-on-surface),.48);font-size:11px}.history-action--plant{color:#4caf50}.history-action--harvest{color:#ff9800}.history-action--steal{color:#e74c3c}.history-action--stolen{color:#e67e22}.history-action--sell{color:#2196f3}.history-value--plus{color:#ff9800}.history-value--minus{color:#4caf50}
.inventory-body{height:320px;max-height:320px;overflow-y:auto;padding:12px!important}.inventory-empty{height:100%;min-height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;color:rgba(var(--v-theme-on-surface),.52);text-align:center}.inventory-empty-icon{font-size:30px;opacity:.82}.inventory-empty small{font-size:11px;color:rgba(var(--v-theme-on-surface),.42)}.inventory-grid{display:grid;grid-template-columns:1fr;gap:8px}.inventory-item{display:grid;grid-template-columns:38px minmax(0,1fr) auto;align-items:center;gap:10px;padding:9px 10px;border-radius:12px;background:rgba(var(--v-theme-surface),.68);border:1px solid rgba(var(--v-theme-on-surface),.07);transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}.inventory-item:hover{transform:translateY(-1px);border-color:rgba(251,146,60,.24);box-shadow:0 6px 16px rgba(15,23,42,.08)}.inventory-icon{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;background:rgba(251,146,60,.12);font-size:23px;line-height:1}.inventory-main{min-width:0}.inventory-name{font-size:13px;font-weight:800;color:rgba(var(--v-theme-on-surface),.84);line-height:1.2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.inventory-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;font-size:11px;color:rgba(var(--v-theme-on-surface),.52);line-height:1.15}.inventory-bonus b{color:#e67e22;font-weight:900}.inventory-sell-btn{min-width:52px!important;padding-inline:10px!important}.inventory-sell-all-btn{min-width:76px!important;padding-inline:10px!important}.sell-avatar{background:rgba(245,158,11,.14);color:#f59e0b}.sell-confirm-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:12px}.sell-confirm-stat{padding:12px;border-radius:12px;background:rgba(245,158,11,.09);border:1px solid rgba(245,158,11,.18);text-align:center}.sell-confirm-stat span{display:block;font-size:11px;color:rgba(var(--v-theme-on-surface),.52);margin-bottom:4px}.sell-confirm-stat b{font-size:22px;color:#f59e0b}.sell-confirm-stat small{margin-left:3px;color:rgba(var(--v-theme-on-surface),.52)}.sell-confirm-list{max-height:180px;overflow:auto;border-radius:12px;border:1px solid rgba(var(--v-theme-on-surface),.07);background:rgba(var(--v-theme-surface),.62)}.sell-confirm-item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 12px;border-bottom:1px solid rgba(var(--v-theme-on-surface),.06);font-size:12px}.sell-confirm-item:last-child{border-bottom:none}.sell-confirm-item span{font-weight:800;color:rgba(var(--v-theme-on-surface),.78);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sell-confirm-item em{font-style:normal;color:#f59e0b;font-weight:900;white-space:nowrap}.sell-confirm-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:16px}.sell-confirm-cancel,.sell-confirm-submit{height:36px!important;border-radius:9px!important;font-size:13px!important;font-weight:800!important;letter-spacing:0!important;padding-inline:18px!important;box-shadow:none!important}.sell-confirm-cancel{background:rgba(var(--v-theme-on-surface),.06)!important;color:rgba(var(--v-theme-on-surface),.54)!important}.sell-confirm-cancel:hover{background:rgba(var(--v-theme-on-surface),.10)!important;color:rgba(var(--v-theme-on-surface),.72)!important}.sell-confirm-submit{min-width:118px!important;background:linear-gradient(135deg,#f59e0b,#fb923c)!important;color:#fff!important;border:1px solid rgba(245,158,11,.32)!important;box-shadow:0 8px 18px rgba(245,158,11,.22)!important}.sell-confirm-submit:hover{transform:translateY(-1px);box-shadow:0 12px 22px rgba(245,158,11,.28)!important}.sell-confirm-submit:active{transform:translateY(0);box-shadow:0 5px 12px rgba(245,158,11,.20)!important}

.buy-avatar{background:rgba(33,150,243,.14);color:#42a5f5;display:flex;align-items:center;justify-content:center}.buy-avatar :deep(.v-icon){display:block;line-height:1}.buy-confirm-tip{padding:10px 12px;margin-bottom:12px;border-radius:12px;background:rgba(33,150,243,.08);border:1px dashed rgba(33,150,243,.18);color:rgba(var(--v-theme-on-surface),.68);font-size:12px;line-height:1.55;text-align:center}

/* 二级拟态样式 */
.neu-action-card{position:relative;display:flex;flex-direction:row;align-items:center;gap:7px;min-height:46px;height:100%;overflow:hidden;background:rgba(var(--v-theme-surface),.88);border:1px solid rgba(76,175,80,.16);border-radius:11px;padding:7px 8px;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}.neu-action-card:hover{transform:translateY(-1px);box-shadow:0 6px 14px rgba(15,23,42,.07)}.neu-action-icon{width:28px;height:28px;display:grid;place-items:center;flex:0 0 28px;border-radius:9px;background:rgba(76,175,80,.09);font-size:19px}.neu-action-content{position:relative;z-index:1;flex:1;min-width:0}.neu-action-label{font-size:12px;font-weight:800;color:rgba(var(--v-theme-on-surface),.84);margin-bottom:2px;line-height:1.15}.neu-action-desc{color:rgba(var(--v-theme-on-surface),.52);font-size:11px;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.neu-btn{height:28px!important;border-radius:999px !important;font-weight:800;letter-spacing:0;font-size:11px!important;min-width:72px!important;box-shadow:none!important}
.neu-action-card--visit{display:grid;grid-template-columns:32px max-content minmax(0,1fr);align-items:center}.visit-action-row{display:grid;grid-template-columns:125px 76px 76px;align-items:center;justify-self:end;gap:6px;position:relative;z-index:1;min-width:0}.visit-btn{width:76px!important;min-width:76px!important;padding-inline:8px!important}.farm-action-btn,.quick-action-btn{height:28px!important;border-radius:4px!important;font-weight:600!important;letter-spacing:0!important;font-size:12px!important;box-shadow:0 2px 6px rgba(15,23,42,.10)!important}.farm-action-btn:not(.v-btn--disabled):hover,.quick-action-btn:not(.v-btn--disabled):hover{box-shadow:0 6px 14px rgba(15,23,42,.14)!important}.quick-action-btn--harvest{background:rgba(245,158,11,.18)!important;color:#fbbf24!important;border:1px solid rgba(245,158,11,.36)!important}.quick-action-btn--harvest:not(.v-btn--disabled):hover{background:rgba(245,158,11,.25)!important;box-shadow:0 6px 16px rgba(245,158,11,.16)!important}.quick-action-btn--plant{background:rgba(34,197,94,.18)!important;color:#4ade80!important;border:1px solid rgba(34,197,94,.34)!important}.quick-action-btn--plant:not(.v-btn--disabled):hover{background:rgba(34,197,94,.24)!important;box-shadow:0 6px 16px rgba(34,197,94,.16)!important}.quick-action-btn--steal{background:rgba(239,68,68,.18)!important;color:#f87171!important;border:1px solid rgba(239,68,68,.36)!important}.quick-action-btn--steal:not(.v-btn--disabled):hover{background:rgba(239,68,68,.25)!important;box-shadow:0 6px 16px rgba(239,68,68,.16)!important}.quick-action-btn--like{background:rgba(236,72,153,.18)!important;color:#f472b6!important;border:1px solid rgba(236,72,153,.36)!important}.quick-action-btn--like:not(.v-btn--disabled):hover{background:rgba(236,72,153,.25)!important;box-shadow:0 6px 16px rgba(236,72,153,.16)!important}.quick-action-btn--visit,.quick-action-btn--random{background:rgba(139,92,246,.18)!important;color:#a78bfa!important;border:1px solid rgba(139,92,246,.36)!important}.quick-action-btn--visit:not(.v-btn--disabled):hover,.quick-action-btn--random:not(.v-btn--disabled):hover{background:rgba(139,92,246,.25)!important;box-shadow:0 6px 16px rgba(139,92,246,.16)!important}.quick-action-btn.v-btn--disabled{background:rgba(var(--v-theme-on-surface),.06)!important;color:rgba(var(--v-theme-on-surface),.42)!important;border-color:rgba(var(--v-theme-on-surface),.10)!important;opacity:1!important}.visit-action-row :deep(.v-field){min-height:28px;border-radius:10px;box-shadow:none}.visit-action-row :deep(.v-field__input){min-height:28px;padding-top:1px;padding-bottom:1px;font-size:12px}.visit-action-row :deep(.v-field__outline){--v-field-border-opacity:.16}
.neu-visit-dialog{background:rgba(var(--v-theme-surface),.98)!important;border-radius:16px!important;border:1px solid rgba(var(--v-theme-on-surface),.10)!important;box-shadow:0 18px 48px rgba(15,23,42,.18)!important;overflow:hidden}
.neu-visit-header{display:flex;align-items:center;gap:14px;padding:14px 16px!important;background:rgba(var(--v-theme-on-surface),.025);border-bottom:1px solid rgba(var(--v-theme-on-surface),.08)!important}
.neu-visit-avatar{width:48px;height:48px;border-radius:14px;background:rgba(76,175,80,.10);border:1px solid rgba(var(--v-theme-on-surface),.08);display:flex;align-items:center;justify-content:center;box-shadow:none;flex-shrink:0}
.neu-visit-info{flex:1;min-width:0}
.neu-visit-name{font-size:16px;font-weight:700;color:#2c3e50;display:flex;align-items:center}
.neu-visit-decor{font-size:11px;color:#888;margin-top:2px}
.neu-visit-actions{display:flex;align-items:center;align-self:center;gap:6px}.neu-visit-actions :deep(.v-btn){align-self:center}.neu-visit-actions :deep(.v-btn:not(.v-btn--icon)){height:32px!important;line-height:32px!important}.visit-like-btn{background:rgba(76,175,80,.18)!important;color:#4ade80!important;border:1px solid rgba(76,175,80,.34)!important;box-shadow:none!important}.visit-like-btn:not(.v-btn--disabled):hover{background:rgba(76,175,80,.24)!important;box-shadow:0 6px 16px rgba(34,197,94,.16)!important}.visit-like-btn.v-btn--disabled{background:rgba(var(--v-theme-on-surface),.06)!important;color:rgba(var(--v-theme-on-surface),.42)!important;border-color:rgba(var(--v-theme-on-surface),.10)!important;opacity:1!important}
.neu-visit-empty{text-align:center;color:#999;padding:20px 0;font-size:13px}
.visit-like-status{padding:9px 12px;margin-bottom:10px;border-radius:12px;background:rgba(76,175,80,.08);border:1px dashed rgba(76,175,80,.18);color:rgba(var(--v-theme-on-surface),.66);font-size:12px;line-height:1.5;text-align:center}.visit-decor-counts{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.visit-decor-chip{padding:3px 9px;border-radius:999px;background:rgba(var(--v-theme-on-surface),.06);color:rgba(var(--v-theme-on-surface),.68);font-size:11px;font-weight:700}.visit-avatar{font-size:24px}.visit-land-locked{padding:12px;border-radius:12px;border:1px dashed rgba(var(--v-theme-on-surface),.16);background:rgba(var(--v-theme-on-surface),.035);text-align:center;color:rgba(var(--v-theme-on-surface),.55);font-weight:700}
.neu-land-section{margin-bottom:14px;padding:14px;border-radius:14px;background:rgba(var(--v-theme-on-surface),.025);border:1px solid rgba(var(--v-theme-on-surface),.07)}
.neu-land-title{font-size:13px;font-weight:600;color:#555;margin-bottom:8px;padding-left:4px}
.neu-plot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:8px}
.neu-visit-plot{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:72px;border-radius:12px;padding:8px 4px;background:rgba(var(--v-theme-surface),.9);border:1px solid rgba(var(--v-theme-on-surface),.10);box-shadow:none;transition:all 0.2s}.neu-visit-plot:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(15,23,42,.08)}
.neu-visit-plot.planted{background:#e8f5e9;border-color:#a5d6a7;box-shadow:none}
.neu-visit-plot.ready{background:#fff8e1;border-color:#ffcc80;box-shadow:none}
.neu-plot-icon-wrap{width:32px;height:32px;display:flex;align-items:center;justify-content:center;margin-bottom:4px}
.neu-plot-emoji{font-size:22px}
.neu-plot-label{font-size:10px;color:#666;text-align:center;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.neu-plot-empty-icon{font-size:16px;opacity:0.3;margin-bottom:4px}
.neu-plot-badge{font-size:9px;padding:1px 6px;border-radius:8px;font-weight:600;margin-top:3px}
.neu-plot-badge.ready{background:#fff3e0;color:#e65100}
.like-avatar{font-size:24px}.like-panel{display:flex;flex-direction:column;gap:12px;padding:2px}.like-panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.like-panel-title{font-size:14px;font-weight:900;color:rgba(var(--v-theme-on-surface),.82)}.like-textarea :deep(.v-field){border-radius:12px;background:rgba(var(--v-theme-surface),.92)}.like-status{padding:10px 12px;border-radius:12px;background:rgba(59,130,246,.08);border:1px dashed rgba(59,130,246,.18);color:rgba(var(--v-theme-on-surface),.68);font-size:12px;line-height:1.55}.today-liked{padding:10px 12px;border-radius:12px;background:rgba(236,72,153,.07);border:1px solid rgba(236,72,153,.12)}.today-liked-title{font-size:12px;font-weight:900;margin-bottom:6px;color:rgba(var(--v-theme-on-surface),.78)}.today-liked-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:3px 0;font-size:12px}.today-liked-item .u{font-weight:800;color:rgba(var(--v-theme-on-surface),.82);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.today-liked-item .r{flex:none;color:#3b82f6;font-weight:700}.like-actions{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap}
.steal-avatar{font-size:24px}.steal-land-section{margin-bottom:14px}.steal-land-title{font-size:13px;font-weight:800;color:rgba(var(--v-theme-on-surface),.78);margin-bottom:8px}.steal-land-locked{padding:12px;border-radius:12px;border:1px dashed rgba(var(--v-theme-on-surface),.16);background:rgba(var(--v-theme-on-surface),.035);text-align:center;color:rgba(var(--v-theme-on-surface),.55);font-weight:700}.steal-plot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:9px}.steal-plot{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-height:76px;border:1px solid rgba(var(--v-theme-on-surface),.10);border-radius:12px;background:rgba(var(--v-theme-surface),.9);cursor:default;color:rgba(var(--v-theme-on-surface),.72);transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease}.steal-plot.planted{background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.28);color:rgba(var(--v-theme-on-surface),.76)}.steal-plot.ready{background:rgba(245,158,11,.14);border-color:rgba(245,158,11,.34);color:rgba(var(--v-theme-on-surface),.82)}.steal-plot.stealable{cursor:pointer;border-color:rgba(239,68,68,.58);box-shadow:0 0 0 1px rgba(239,68,68,.18)}.steal-plot.stealable:hover{transform:translateY(-2px);background:rgba(239,68,68,.12);box-shadow:0 8px 18px rgba(239,68,68,.16)}.steal-plot.stolen{background:rgba(239,68,68,.10);border-color:rgba(239,68,68,.24);opacity:.65;cursor:not-allowed}.steal-plot small{font-size:10px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:rgba(var(--v-theme-on-surface),.72)}.steal-badge{position:absolute;right:4px;top:4px;padding:1px 5px;border-radius:999px;font-size:9px;font-weight:800}.steal-badge.ready{background:rgba(239,68,68,.16);color:#f87171}.steal-badge.stolen{background:rgba(var(--v-theme-on-surface),.10);color:rgba(var(--v-theme-on-surface),.58)}
.slide-fade-enter-active{transition:all 0.3s ease-out}
.slide-fade-leave-active{transition:all 0.2s ease-in}
.slide-fade-enter-from{transform:translateY(12px);opacity:0}
.slide-fade-leave-to{transform:translateY(-8px);opacity:0}
@media(max-width:1100px){.seed-interact-row{grid-template-columns:1fr}.seed-grid{grid-template-columns:repeat(auto-fill,minmax(188px,1fr))}}
@media(max-width:600px){.siqi-page{padding:14px}.siqi-topbar{align-items:flex-start;gap:10px}.siqi-topbar__left{min-width:0}.siqi-topbar__right :deep(.v-btn){min-width:36px!important;padding-inline:0!important}.seed-grid{grid-template-columns:1fr}.land-section--locked{padding:12px 14px}.land-section--locked .land-title{margin-bottom:0}.land-section--locked .plot-grid{display:none}.land-section--locked .land-locked-mobile-hint{display:block;margin-top:6px;font-size:11px;color:rgba(var(--v-theme-on-surface),.45)}.farm-interact-subtitle{display:none}.farm-interact-body{padding:14px !important}.neu-action-card{min-height:auto;padding:14px}.neu-action-card--visit{grid-template-columns:32px minmax(0,1fr);row-gap:10px}.neu-action-card--visit .neu-action-icon{grid-column:1;grid-row:1}.neu-action-card--visit .neu-action-content{grid-column:2;grid-row:1}.visit-action-row{grid-column:1/-1;grid-template-columns:minmax(0,1fr) 72px 72px;justify-self:stretch;width:100%}.visit-action-row .v-input{grid-column:auto;min-width:0}.visit-action-row .v-btn{width:100%!important;min-width:0!important;padding-inline:6px!important}}
</style>
