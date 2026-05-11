def form(site_options) -> list:
    """
    拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
    """
    # 动态判断MoviePilot版本，决定定时任务输入框组件类型
    from app.core.config import settings
    version = getattr(settings, "VERSION_FLAG", "v1")
    cron_field_component = "VCronField" if version == "v2" else "VTextField"

    return [
        {
            'component': 'VForm',
            'content': [
                {
                    'component': 'VCard',
                    'props': {
                        'class': 'mt-0'
                    },
                    'content': [
                        {
                            'component': 'VCardTitle',
                            'props': {
                                'class': 'd-flex align-center'
                            },
                            'content': [
                                {
                                    'component': 'VIcon',
                                    'props': {
                                        'style': 'color: #16b1ff;',
                                        'class': 'mr-2'
                                    },
                                    'text': 'mdi-cog'
                                },
                                {
                                    'component': 'span',
                                    'text': '基础设置'
                                }
                            ]
                        },
                        {
                            'component': 'VDivider'
                        },
                        {
                            'component': 'VCardText',
                            'content': [
                                {
                                    'component': 'VRow',
                                    'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'enabled',
                                                        'label': '启用插件',
                                                        'color': 'primary'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'notify',
                                                        'label': '发送通知',
                                                        'color': 'info'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'use_proxy',
                                                        'label': '启用代理',
                                                        'color': 'success'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'onlyonce',
                                                        'label': '立即运行一次',
                                                        'color': 'warning'
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'component': 'VCard',
                    'props': {
                        'class': 'mt-3'
                    },
                    'content': [
                        {
                            'component': 'VCardTitle',
                            'props': {
                                'class': 'd-flex align-center'
                            },
                            'content': [
                                {
                                    'component': 'VIcon',
                                    'props': {
                                        'style': 'color: #16b1ff;',
                                        'class': 'mr-2'
                                    },
                                    'text': 'mdi-clock-outline'
                                },
                                {
                                    'component': 'span',
                                    'text': '执行设置'
                                }
                            ]
                        },
                        {
                            'component': 'VDivider'
                        },
                        {
                            'component': 'VCardText',
                            'content': [
                                {
                                    'component': 'VRow',
                                    'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 4
                                            },
                                            'content': [
                                                {
                                                    'component': cron_field_component,
                                                    'props': {
                                                        'model': 'cron',
                                                        'label': '执行周期',
                                                        'placeholder': '5位cron表达式，留空自动'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 4
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'model': 'interval_cnt',
                                                        'label': '消息发送间隔(秒)',
                                                        'items': [
                                                            {'title': '1秒', 'value': 1},
                                                            {'title': '2秒', 'value': 2}
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 4
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'model': 'feedback_timeout',
                                                        'label': '反馈等待时间(秒)',
                                                        'items': [
                                                            {'title': '1秒', 'value': 1},
                                                            {'title': '2秒', 'value': 2},
                                                            {'title': '3秒', 'value': 3},
                                                            {'title': '4秒', 'value': 4},
                                                            {'title': '5秒', 'value': 5}
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                    ]
                                },
                                {
                                    'component': 'VRow',
                                    'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'model': 'retry_count',
                                                        'label': '喊话失败重试次数',
                                                        'items': [
                                                            {'title': '0次(不重试)', 'value': 0},
                                                            {'title': '1次', 'value': 1},
                                                            {'title': '2次', 'value': 2},
                                                            {'title': '3次', 'value': 3}
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'model': 'retry_interval',
                                                        'label': '喊话失败重试间隔(分钟)',
                                                        'items': [
                                                            {'title': '5分钟', 'value': 5},
                                                            {'title': '10分钟', 'value': 10},
                                                            {'title': '15分钟', 'value': 15},
                                                            {'title': '30分钟', 'value': 30},
                                                            {'title': '60分钟', 'value': 60},
                                                            {'title': '120分钟', 'value': 120}
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'model': 'zm_interval',
                                                        'label': '独立织梦喊话间隔(秒)',
                                                        'items': [{'title': f'{i}秒', 'value': i} for i in range(60, 121)]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'model': 'retry_notify',
                                                        'label': '启用重试通知',
                                                        'items': [
                                                            {'title': '关闭', 'value': False},
                                                            {'title': '开启', 'value': True}
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'component': 'VCard',
                    'props': {
                        'class': 'mt-3'
                    },
                    'content': [
                        {
                            'component': 'VCardTitle',
                            'props': {
                                'class': 'd-flex align-center'
                            },
                            'content': [
                                {
                                    'component': 'VIcon',
                                    'props': {
                                        'style': 'color: #16b1ff;',
                                        'class': 'mr-2'
                                    },
                                    'text': 'mdi-web'
                                },
                                {
                                    'component': 'span',
                                    'text': '站点设置'
                                }
                            ]
                        },
                        {
                            'component': 'VDivider'
                        },
                        {
                            'component': 'VCardText',
                            'content': [
                                {
                                    'component': 'VRow',
                                    'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'get_feedback',
                                                        'label': '获取反馈',
                                                        'color': 'primary'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'qingwa_daily_bonus',
                                                        'label': '青蛙福利购买',
                                                        'color': 'info'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'longpt_daily_lottery',
                                                        'label': 'LongPT每日抽奖',
                                                        'color': 'success'
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12,
                                                'md': 3
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'thirteencity_auto_buy_blessing',
                                                        'label': '13City勋章购买',
                                                        'color': 'warning'
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    'component': 'VRow',
                                    'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12
                                            },
                                            'content': [
                                                {
                                                    'component': 'VSelect',
                                                    'props': {
                                                        'chips': True,
                                                        'multiple': True,
                                                        'model': 'chat_sites',
                                                        'label': '选择站点',
                                                        'items': site_options
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    'component': 'VRow',
                                    'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {
                                                'cols': 12
                                            },
                                            'content': [
                                                {
                                                    'component': 'VTextarea',
                                                    'props': {
                                                        'model': 'sites_messages',
                                                        'label': '自定义消息',
                                                        'rows': 7,
                                                        'placeholder': '每一行一个配置，配置方式：\n'
                                                                        '站点名称|消息内容1|消息内容2|...|60s\n'
                                                                        '末尾支持自定义间隔时间(如60s)，不填则使用默认间隔。\n'
                                                                        '同名站点消息配置多行支持消息合并。\n'
                                                                        '织梦站点消息配置建议将求电力放到最后面：\n'
                                                                        '织梦|消息内容1|消息内容2|...|皮总，求电力\n'
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'component': 'VCard',
                    'props': {
                        'class': 'mt-3'
                    },
                    'content': [
                        {
                            'component': 'VCardTitle',
                            'props': {
                                'class': 'd-flex align-center'
                            },
                            'content': [
                                {
                                    'component': 'VIcon',
                                    'props': {
                                        'style': 'color: #16b1ff;',
                                        'class': 'mr-2'
                                    },
                                    'text': 'mdi-information'
                                },
                                {
                                    'component': 'span',
                                    'text': '使用说明'
                                }
                            ]
                        },
                        {
                            'component': 'VDivider'
                        },
                        {
                            'component': 'VCardText',
                            'props': {
                                'class': 'px-6 pb-6'
                            },
                            'content': [
                                {
                                    'component': 'VList',
                                    'props': {'lines': 'two', 'density': 'comfortable'},
                                    'content': [
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'd-flex align-items-start'},
                                                    'content': [
                                                        {'component': 'VIcon', 'props': {'color': 'primary', 'class': 'mt-1 mr-2'}, 'text': 'mdi-calendar-clock'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '执行周期说明'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'content': [
                                                        {'component': 'div', 'text': '支持以下三种方式：', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '📅 5位cron表达式', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '⏰ 配置间隔（小时），如2.3/9-23（9-23点之间每隔2.3小时执行一次）', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '🔄 周期不填默认9-23点随机执行1次'}
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'd-flex align-items-start'},
                                                    'content': [
                                                        {'component': 'VIcon', 'props': {'color': 'warning', 'class': 'mt-1 mr-2'}, 'text': 'mdi-alert'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '特别说明X3(重要的事情说3遍)'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'content': [
                                                        {'component': 'div', 'text': '• 请不要使用插件执行（包含发送无意义的群聊区喊话、刷屏等行为）', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '• 站点选择中已有的站点可以进行喊话，如果后续有新增站点再更新加入', 'props': {'class': 'mb-1'}},
                                                        {
                                                            'component': 'div',
                                                            'props': {'class': 'mb-1'},
                                                            'content': [
                                                                {'component': 'span', 'text': '• 配置好喊话内容后请使用'},
                                                                {'component': 'span', 'props': {'style': 'color: green; font-weight: bold;'}, 'text': '【立即运行一次】'},
                                                                {'component': 'span', 'text': '测试喊话是否正常、确保不会重复喊话刷屏'}
                                                            ]
                                                        },
                                                        {'component': 'div', 'text': '• 请确保定时Cron表达式设置正确，避免频繁执行喊话任务导致刷屏', 'props': {'class': 'mb-1'}},
                                                        {
                                                            'component': 'div',
                                                            'content': [
                                                                {'component': 'span', 'text': '• 如果由于不正确的使用导致'},
                                                                {'component': 'span', 'props': {'style': 'color: red; text-decoration: underline; font-weight: bold;'}, 'text': '账号封禁'},
                                                                {'component': 'span', 'text': '的请自行承担后果！'}
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'd-flex align-items-start'},
                                                    'content': [
                                                        {'component': 'VIcon', 'props': {'color': 'error', 'class': 'mt-1 mr-2'}, 'text': 'mdi-application-settings'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '织梦喊话说明'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'content': [
                                                        {'component': 'div', 'text': '🎯 只要选中了织梦站点，插件就会自动使用独立织梦喊话逻辑，与其他站点分开处理', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '⏰ 插件会自动获取织梦最新电力奖励邮件时间，用于计算下次执行时间', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '🔄 普通站点继续按统一周期执行，织梦站点自动走独立调度', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '⏱️ 独立织梦喊话间隔：可配置60-120秒之间的喊话间隔，避免过于频繁的喊话', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '🛡️ 防重复执行：内置10分钟冷却机制，防止短时间内重复执行喊话任务', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '💡 无需额外开关，选中织梦站点后会自动启用该逻辑', 'props': {'class': 'mb-3'}},
                                                        {'component': 'div', 'text': '📅 织梦定时器说明：', 'props': {'class': 'text-subtitle-2 font-weight-bold mt-2 mb-1'}},
                                                        {'component': 'div', 'text': '• 首次运行时会自动获织梦最新电力奖励邮件的时间，用于计算下次执行时间注册"群聊区 - 织梦定时任务"', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '• 每次执行完喊话任务后会更新获取的邮件时间，确保定时准确', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '• 如果获取的邮件时间对比上次获取的邮件已超过24小时,将立即执行织梦喊话任务', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '• 重启或重载插件时会从持久化配置中获取邮件时间，确保定时任务正常运行', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '• 内置10分钟冷却机制，防止短时间内重复执行喊话任务', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '• 邮件时间获取失败时，最多重试3次，超过后使用默认24小时间隔'}
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'd-flex align-items-start'},
                                                    'content': [
                                                        {'component': 'VIcon', 'props': {'color': 'success', 'class': 'mt-1 mr-2'}, 'text': 'mdi-timer-cog'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '自定义消息间隔说明'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'content': [
                                                        {'component': 'div', 'text': '⏱️ 支持为每一行消息单独设置发送等待间隔（单位：秒）', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '💡 配置格式：在消息行末尾添加竖线和时间，例如：站点名|消息内容|60s', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '⚠️ 优先级说明：自定义间隔 > 织梦独立间隔 > 全局默认间隔', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '🔄 重试机制：消息发送失败重试时，也会优先使用该自定义间隔'}
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'd-flex align-items-start'},
                                                    'content': [
                                                        {'component': 'VIcon', 'props': {'color': 'info', 'class': 'mt-1 mr-2'}, 'text': 'mdi-message-reply-text'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '获取反馈功能'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'content': [
                                                        {'component': 'div', 'text': '📊 获取喊话后的站点反馈(奖励信息)，有助于了解站点对喊话的响应情况', 'props': {'class': 'mb-1'}},
                                                        {'component': 'div', 'text': '📈 反馈信息包括奖励类型、数量和时间，有助于分析站点奖励机制'}
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ], {
        "enabled": False,
        "notify": True,
        "cron": "",
        "onlyonce": False,
        "interval_cnt": 2,
        "chat_sites": [],
        "sites_messages": "",
        "get_feedback": True,
        "feedback_timeout": 5,
        "use_proxy": True,
        "qingwa_daily_bonus": False,
        "longpt_daily_lottery": False,
        "thirteencity_auto_buy_blessing": False,
        "retry_count": 2,
        "retry_interval": 10,
        "zm_interval": 60,
        "retry_notify": False
    }