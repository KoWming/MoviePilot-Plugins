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
                                    'text': '基本设置'
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
                                        }
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
                                                    'component': 'VSwitch',
                                                    'props': {
                                                        'model': 'retry_notify',
                                                        'label': '启用重试通知',
                                                        'hint': '开启后，当喊话失败需要重试时会发送通知提醒；关闭后仅执行重试，不发送通知。',
                                                        'persistent-hint': True,
                                                        'color': 'error'
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
                                                        'model': 'zm_independent',
                                                        'label': '独立织梦喊话',
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
                                                        'model': 'qingwa_daily_bonus',
                                                        'label': '青蛙福利购买',
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
                                                        'model': 'longpt_daily_lottery',
                                                        'label': 'LongPT每日抽奖',
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
                                                                        '站点名称|消息内容1|消息内容2|消息内容3|...\n'
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
                                    'props': {
                                        'lines': 'two',
                                        'density': 'comfortable'
                                    },
                                    'content': [
                                        {
                                            'component': 'VListItem',
                                            'props': {
                                                'lines': 'two'
                                            },
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'd-flex align-items-start'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'primary',
                                                                'class': 'mt-1 mr-2'
                                                            },
                                                            'text': 'mdi-calendar-clock'
                                                        },
                                                        {
                                                            'component': 'div',
                                                            'props': {
                                                                'class': 'text-subtitle-1 font-weight-regular mb-1',
                                                                'style': 'color: #444;'
                                                            },
                                                            'text': '执行周期说明'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'text': '支持以下三种方式：'
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '📅 5位cron表达式'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '⏰ 配置间隔（小时），如2.3/9-23（9-23点之间每隔2.3小时执行一次）'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '🔄 周期不填默认9-23点随机执行1次'
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {
                                                'lines': 'two'
                                            },
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'd-flex align-items-start'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'warning',
                                                                'class': 'mt-1 mr-2'
                                                            },
                                                            'text': 'mdi-alert'
                                                        },
                                                        {
                                                            'component': 'div',
                                                            'props': {
                                                                'class': 'text-subtitle-1 font-weight-regular mb-1',
                                                                'style': 'color: #444;'
                                                            },
                                                            'text': '特别说明X3(重要的事情说3遍)'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 请不要使用插件执行（包含发送无意义的群聊区喊话、刷屏等行为）'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 站点选择中已有的站点可以进行喊话，如果后续有新增站点再更新加入'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 配置好喊话内容后请使用'
                                                        },
                                                        {
                                                            'component': 'span',
                                                            'props': {
                                                                'style': 'color: green;'
                                                            },
                                                            'text': '【立即运行一次】'
                                                        },
                                                        {
                                                            'component': 'span',
                                                            'text': '测试喊话是否正常、确保不会重复喊话刷屏'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 请确保定时Cron表达式设置正确，避免频繁执行喊话任务导致刷屏'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 如果由于不正确的使用导致'
                                                        },
                                                        {
                                                            'component': 'span',
                                                            'props': {
                                                                'style': 'color: red; text-decoration: underline;'
                                                            },
                                                            'text': '账号封禁'
                                                        },
                                                        {
                                                            'component': 'span',
                                                            'text': '的请自行承担后果！'
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {
                                                'lines': 'two'
                                            },
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'd-flex align-items-start'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'error',
                                                                'class': 'mt-1 mr-2'
                                                            },
                                                            'text': 'mdi-application-settings'
                                                        },
                                                        {
                                                            'component': 'div',
                                                            'props': {
                                                                'class': 'text-subtitle-1 font-weight-regular mb-1',
                                                                'style': 'color: #444;'
                                                            },
                                                            'text': '独立织梦喊话功能'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '🎯 开启后织梦站点将独立执行喊话任务，与其他站点分开处理'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '⏰ 开启后获取织梦最新电力奖励邮件的时间，用于计算下次执行时间'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '🔄 关闭时织梦站点将与其他站点一起执行喊话任务，使用统一的执行周期'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '⏱️ 独立织梦喊话间隔：可配置60-120秒之间的喊话间隔，避免过于频繁的喊话'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '🛡️ 防重复执行：内置10分钟冷却机制，防止短时间内重复执行喊话任务'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '💡 建议开启此功能，可以更精确的执行喊话任务'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8',
                                                        'style': 'color: #444;'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '📅 织梦定时器说明：'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 首次运行时会自动获织梦最新电力奖励邮件的时间，用于计算下次执行时间注册"群聊区 - 织梦定时任务"'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 每次执行完喊话任务后会更新获取的邮件时间，确保定时准确'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 如果获取的邮件时间对比上次获取的邮件已超过24小时,将立即执行织梦喊话任务'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 重启或重载插件时会从持久化配置中获取邮件时间，确保定时任务正常运行'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 内置10分钟冷却机制，防止短时间内重复执行喊话任务'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '  • 邮件时间获取失败时，最多重试3次，超过后使用默认24小时间隔'
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {
                                                'lines': 'two'
                                            },
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'd-flex align-items-start'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'success',
                                                                'class': 'mt-1 mr-2'
                                                            },
                                                            'text': 'mdi-gift'
                                                        },
                                                        {
                                                            'component': 'div',
                                                            'props': {
                                                                'class': 'text-subtitle-1 font-weight-regular mb-1',
                                                                'style': 'color: #444;'
                                                            },
                                                            'text': '青蛙每日福利功能'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '🎁 开启后会自动执行任务购买青蛙站点的每日福利（1蝌蚪兑换1000蝌蚪）'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '📅 每日限购1次，系统会自动检查是否已购买，避免重复购买'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '💡 购买结果会在通知消息中显示，包括成功或失败的状态'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '⚠️ 需要确保青蛙站点已正确配置且用户有足够的蝌蚪余额'
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {
                                                'lines': 'two'
                                            },
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'd-flex align-items-start'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'info',
                                                                'class': 'mt-1 mr-2'
                                                            },
                                                            'text': 'mdi-message-reply-text'
                                                        },
                                                        {
                                                            'component': 'div',
                                                            'props': {
                                                                'class': 'text-subtitle-1 font-weight-regular mb-1',
                                                                'style': 'color: #444;'
                                                            },
                                                            'text': '获取反馈功能'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '📊 获取喊话后的站点反馈(奖励信息)，有助于了解站点对喊话的响应情况'
                                                        }
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {
                                                        'class': 'text-body-2 ml-8'
                                                    },
                                                    'content': [
                                                        {
                                                            'component': 'span',
                                                            'text': '📈 反馈信息包括奖励类型、数量和时间，有助于分析站点奖励机制'
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
        "zm_independent": True,
        "qingwa_daily_bonus": False,
        "longpt_daily_lottery": False,
        "retry_count": 2,
        "retry_interval": 10,
        "zm_interval": 60,
        "retry_notify": True
    }