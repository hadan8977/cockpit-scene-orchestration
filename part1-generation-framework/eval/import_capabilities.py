#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把公司最新的座舱原子能力表（notes/inputs/座舱原子能力-最新.xlsx，2026-07 版）导成 vocab.json v2。
保留旧题集里已用的能力名；新增能力按表命名；每条带 meta：来源、成熟度、分组、安全级、执行映射。
成熟度：released（UX已出/已平台化）、no_ux（能力有、UX未出）、sprint（排了 sprint 或版本号）、planned（待定）、proposed（我们提议，表里没有，需要共建）。
  python3 import_capabilities.py && python3 registry.py build && python3 registry.py render && python3 registry.py schema
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
LV = ["1挡", "2挡", "3挡", "关闭"]
WIN = ["关闭"] + ["%d%%" % i for i in range(10, 101, 10)]
PCT10 = ["%d%%" % i for i in range(10, 101, 10)]
SW = ["开启", "关闭"]

def M(source, maturity, group, cls="A", exec_map=None, note=""):
    d = {"source": source, "maturity": maturity, "group": group, "class": cls}
    if exec_map: d["exec"] = exec_map
    if note: d["note"] = note
    return d

conditions, actions, meta = {}, {}, {"conditions": {}, "actions": {}}
def C(name, values, m): conditions[name] = values; meta["conditions"][name] = m
def A(name, values, m): actions[name] = values; meta["actions"][name] = m

# ---------- 条件（当满足条件） ----------
for zh, src in [("主驾车窗", "门窗/主驾车窗"), ("副驾车窗", "门窗/副驾车窗"), ("左后排车窗", "门窗/左后排车窗"), ("右后排车窗", "门窗/右后排车窗"), ("任意车窗", "门窗/任意车窗")]:
    C(zh, SW, M(src, "released", "车窗", "B"))
C("空调总开关", SW, M("空调/空调开关", "released", "空调与空气")); C("MAX AC", SW, M("空调/MAX AC 极速降温", "no_ux", "空调与空气"))
C("极速升温", SW, M("空调/极速升温", "no_ux", "空调与空气")); C("AUTO模式", SW, M("空调/AUTO模式", "released", "空调与空气"))
C("前风窗除雾", SW, M("空调/前风窗除雾", "released", "空调与空气")); C("内外循环设置", ["内循环", "外循环"], M("空调/内外循环状态", "released", "空调与空气"))
C("自动空气净化", SW, M("空调/自动空气净化", "released", "空调与空气"))
for zh, src in [("主驾座椅", "座椅/主驾座椅 入座离座"), ("副驾座椅", "座椅/副驾座椅 入座离座"), ("任意座椅", "座椅/任意位置 入座离座")]:
    C(zh, ["有人", "无人"], M(src, "released", "乘员", note="后排没有占位信号，用后排安全带作代理"))
for seat in ["主驾", "副驾", "左后排", "右后排"]:
    C(seat + "座椅加热", SW, M("舒适/%s座椅加热" % seat, "released", "座椅")); C(seat + "座椅通风", SW, M("舒适/%s座椅通风" % seat, "released", "座椅"))
C("主驾座椅按摩", SW, M("舒适/主驾座椅按摩", "released", "座椅")); C("副驾座椅按摩", SW, M("舒适/副驾座椅按摩", "released", "座椅"))
for zh, src in [("左前门", "门窗/主驾车门"), ("右前门", "门窗/副驾车门"), ("左后门", "门窗/左后排车门"), ("右后门", "门窗/右后排车门"), ("任意车门", "门窗/任意车门"), ("尾门", "门窗/后备箱"), ("前备箱", "门窗/前备箱")]:
    C(zh, SW, M(src, "released", "门", "B"))
C("车锁", ["有门未锁", "全部上锁"], M("门窗/车锁", "released", "门", note="离车事件的真实信号"))
C("香氛开关", SW, M("舒适/香氛开关", "released", "氛围"))
C("挡位", ["挡位N", "挡位D", "挡位P", "挡位R"], M("驾驶/挡位", "released", "车辆状态", "C"))
C("电量", {"range": [1, 100, 1, "%"]}, M("驾驶/车辆电量 上升至/下降至", "released", "车辆状态"))
C("车速", {"range": [0, 200, 10, "KM/小时"]}, M("驾驶/车辆速度", "released", "车辆状态"))
C("续航里程", {"range": [1, 100, 1, "%"]}, M("驾驶/续航里程（百分比）", "released", "车辆状态", note="表里没有公里数与到目的地距离，只有百分比"))
for zh in ["主驾", "副驾", "左后排", "右后排", "后排中间", "任意"]:
    C(zh + "安全带", ["系上", "解开"], M("驾驶/%s安全带" % zh, "released", "乘员", note="后排有人的代理信号" if "后" in zh else ""))
C("车内温度", {"range": [-10, 50, 1, "℃"]}, M("环境/车内温度", "released", "环境")); C("车外温度", {"range": [-10, 50, 1, "℃"]}, M("环境/车外温度", "released", "环境"))
C("车内PM2.5", {"range": [0, 250, 10, "μg/m³"]}, M("环境/车内PM2.5", "released", "环境"))
for zh in ["近光灯", "远光灯", "后雾灯"]:
    C(zh, SW, M("灯光/" + zh, "released", "灯光", note="近光灯开启可作天黑代理" if zh == "近光灯" else ""))
C("媒体音量", {"range": [0, 100, 10, "%"]}, M("声音/音量 媒体音量", "released", "声音"))
C("无线充电", ["充电中", "未充电"], M("设备/主驾充电面板", "released", "设备", note="手机放上去了的代理"))
C("位置", ["家", "公司", "收藏地点"], M("位置/在某地 不在某地", "planned", "条件语义", note="op 用 == 与 !=；地点搜索型暂不放开"))
C("导航目的地", ["家", "公司", "收藏地点"], M("导航/导航至", "planned", "条件语义", note="导航状态、预计到达时间、剩余距离已从表里删除"))
C("时段", ["清晨", "上午", "中午", "下午", "傍晚", "夜晚", "深夜"], M("时间/生效时间 + 生效范围 startTime/endTime", "released", "条件语义", exec_map="映射到生效范围的时间段", note="派生：时段名对应固定时间段"))
C("星期类型", ["工作日", "休息日", "节假日"], M("生效范围/重复 weekDays", "released", "条件语义", exec_map="工作日=[1..5]，休息日=[6,7]", note="节假日含调休需要节假日表，表里没有，proposed"))
C("天气", ["晴", "雨", "雪", "暴晒", "高温", "低温"], M("无信号；小塔能播天气说明有天气服务", "proposed", "条件语义", note="需接天气服务；暴晒可用车内温度加停车时长代理"))
C("行程事件", ["出发", "到达", "停车等人", "离车"], M("由挡位、入座、车锁、位置组合派生", "proposed", "条件语义", exec_map="出发=挡位D且主驾有人；到达=挡位P且位置命中；停车等人=挡位P且主驾有人且停留超过阈值；离车=主驾无人且全部上锁"))

# ---------- 动作（就执行） ----------
for zh, src, mat in [("空调总开关", "空调/空调开关", "released"), ("MAX AC", "空调/MAX AC 极速降温", "released"), ("极速升温", "空调/极速升温", "released"), ("AUTO模式", "空调/AUTO模式", "released"),
                     ("温区同步", "空调/温区同步", "released"), ("前风窗除雾", "空调/前风窗除雾", "released"), ("AC开关", "空调/AC开关", "released"), ("ECO", "空调/ECO", "released"),
                     ("主驾模式", "空调/主驾模式", "released"), ("自动空气净化", "空调/自动空气净化", "released"), ("后视镜加热", "空调/后视镜加热", "released"), ("空气自干燥", "空调/空调自干燥", "released")]:
    A(zh, SW, M(src, mat, "空调与空气"))
A("内外循环设置", ["内循环", "外循环"], M("空调/内外循环", "released", "空调与空气"))
A("主驾温度控制", {"range": [18, 32, 1, "℃"]}, M("空调/温度控制 主驾温度", "released", "空调与空气", note="接口支持 0.5 步长，prompt 只用整数"))
A("副驾温度控制", {"range": [18, 32, 1, "℃"]}, M("空调/温度控制 副驾温度", "released", "空调与空气"))
A("前排风量调节", ["%d挡" % i for i in range(1, 9)], M("空调/风量调节", "released", "空调与空气"))
A("出风模式设置", ["吹面", "吹脚", "吹面吹脚", "吹脚除霜", "除霜"], M("空调/出风模式", "released", "空调与空气"))
for zh in ["左前门", "右前门", "左后门", "右后门"]:
    A(zh, SW, M("舒适/" + zh, "planned", "门", "B", note="只在停车且确认后执行"))
A("香氛开关", SW, M("香氛/香氛开关", "no_ux", "氛围")); A("香氛类型", ["类型1", "类型2", "类型3"], M("香氛/香氛类型", "released", "氛围", note="前置：香氛开关开启"))
A("香氛浓度", ["淡雅", "自然", "馥郁"], M("香氛/香氛浓度", "released", "氛围", note="前置：香氛开关开启"))
for zh in ["主驾车窗", "副驾车窗", "左后排车窗", "右后排车窗"]:
    A(zh, WIN, M("门窗/" + zh, "released", "车窗", "B"))
A("低速行人警报音", ["开启", "关闭", "微风", "梦幻", "无尽"], M("声音/低速行人警报音", "released", "声音", "C", note="表里允许关闭；本方案禁止值=关闭（R138、FMVSS 141）；三种音色仅国内"))
A("一键静音", SW, M("声音/一键静音", "no_ux", "声音"))
A("音量", {"range": [0, 100, 10, "%"]}, M("声音/音量 媒体音量", "released", "声音", exec_map="媒体音量"))
A("导航音量", {"range": [0, 100, 10, "%"]}, M("声音/音量 导航音量", "released", "声音")); A("语音音量", {"range": [0, 100, 10, "%"]}, M("声音/音量 语音音量", "released", "声音"))
A("音效", ["立体声", "音乐厅", "VIP", "影院"], M("声音/音效", "released", "声音"))
A("声场", ["全车模式", "前排模式", "主驾模式"], M("声音/声场", "released", "声音", note="“别吵醒后排”的正解：声场切前排或主驾"))
A("声浪", ["静音", "超跑", "量子", "无尽"], M("声音/声浪", "released", "声音"))
A("小塔播报", ["播放天气", "自定义内容"], M("小塔/小塔播报", "released", "话", exec_map="自定义内容=契约里的 say 文本", note="六元素里的“话”有真实能力承接"))
A("氛围灯开关", SW, M("灯光/氛围灯开关", "released", "氛围")); A("音乐律动", ["模式1", "模式2", "模式3", "关闭"], M("灯光/氛围灯音乐律动", "released", "氛围"))
A("氛围灯亮度", PCT10, M("灯光/氛围灯亮度 1至10", "released", "氛围", exec_map="10%→1 … 100%→10", note="表里没有氛围灯颜色"))
for seat in ["主驾", "副驾", "左后排", "右后排"]:
    A(seat + "座椅加热", LV, M("舒适/%s座椅加热" % seat, "released", "座椅")); A(seat + "座椅通风", LV, M("舒适/%s座椅通风" % seat, "released", "座椅"))
for seat in ["主驾", "副驾"]:
    A(seat + "座椅按摩强度", ["1挡", "2挡", "3挡"], M("舒适/%s座椅按摩 强度 Level1-3" % seat, "released", "座椅", note="前置：按摩开启"))
    A(seat + "座椅按摩模式", ["关闭", "波浪", "猫步", "蛇形", "肩部", "腰部"], M("舒适/%s座椅按摩 模式" % seat, "sprint", "座椅", note="五种模式排在 sprint1"))
A("方向盘加热", SW, M("舒适/方向盘加热", "released", "其他"))
A("延时", {"range": [1, 600, 1, "秒"]}, M("时间/延时 0-59分0-59秒", "released", "编排", note="场景内顺序与时间线靠它"))
A("导航目的地", ["家", "公司", "收藏地点"], M("导航/目的地", "sprint", "供", "B", note="家、公司在 26409；收藏地点待定；行驶中要确认"))
A("多媒体", ["播放", "暂停", "下一首", "上一首"], M("娱乐/多媒体", "sprint", "声音"))
A("音乐播放", ["想念", "放松", "庆祝", "专注", "安静", "浪漫", "雨天", "白噪音", "停止"], M("娱乐/QQ音乐 网易云 播放指定音乐（待定）", "proposed", "声音", exec_map="情绪类歌单→播放指定音乐或猜你喜欢；停止→多媒体暂停", note="表里只有列表播放与指定歌曲，情绪歌单要与娱乐域共建"))
A("彩蛋", ["生日动效", "情人节动效"], M("娱乐/彩蛋", "released", "惊喜", note="自定义动效待定"))
A("进入情景模式", ["休憩模式", "露营模式", "洗车模式", "后排查看", "离车不下电模式", "多人同乘隐私模式"], M("娱乐/情景模式 进入", "planned", "预设", "B", note="官方预设；用户点名时优先调用而非重新组合"))
A("退出情景模式", ["休憩模式", "露营模式", "洗车模式", "后排查看", "离车不下电模式", "多人同乘隐私模式"], M("娱乐/情景模式 退出", "planned", "预设"))
A("屏幕模式", ["白天模式", "黑夜模式"], M("屏幕/模式", "released", "屏幕")); A("屏幕亮度", PCT10, M("屏幕/亮度", "released", "屏幕"))
A("无线充电", SW, M("设备/主驾充电面板", "released", "设备")); A("电动遮阳帘", ["关闭"] + PCT10, M("设备/电动遮阳帘 开度", "released", "设备", note="关闭=0%"))

EN = {"任意车窗": ("window.any", "any window"), "极速升温": ("hvac.max_heat", "max heat"), "任意座椅": ("seat.any.occupied", "any seat occupancy"),
      "任意车门": ("door.any", "any door"), "车锁": ("door.lock", "door lock state"), "续航里程": ("vehicle.range_pct", "remaining range %"),
      "主驾安全带": ("belt.driver", "driver seat belt"), "副驾安全带": ("belt.passenger", "passenger seat belt"), "左后排安全带": ("belt.rear_left", "rear left seat belt"),
      "右后排安全带": ("belt.rear_right", "rear right seat belt"), "后排中间安全带": ("belt.rear_middle", "rear middle seat belt"), "任意安全带": ("belt.any", "any seat belt"),
      "近光灯": ("light.low_beam", "low beam"), "远光灯": ("light.high_beam", "high beam"), "后雾灯": ("light.rear_fog", "rear fog light"),
      "媒体音量": ("audio.media_volume.state", "media volume state"), "无线充电": ("device.wireless_charger", "wireless charger"),
      "位置": ("ctx.place", "place"), "导航目的地": ("nav.destination", "navigation destination"), "副驾温度控制": ("hvac.temp.passenger", "passenger temperature"),
      "后视镜加热": ("mirror.heat", "mirror heating"), "一键静音": ("audio.mute", "mute"), "导航音量": ("audio.nav_volume", "navigation volume"),
      "语音音量": ("audio.voice_volume", "voice volume"), "音效": ("audio.effect", "sound effect"), "声场": ("audio.soundstage", "sound stage"),
      "声浪": ("audio.engine_sound", "engine sound"), "小塔播报": ("voice.announce", "assistant announce"), "延时": ("flow.delay", "delay"),
      "多媒体": ("media.transport", "media transport"), "彩蛋": ("surprise.easter_egg", "easter egg"), "进入情景模式": ("preset.enter", "enter scenario mode"),
      "退出情景模式": ("preset.exit", "exit scenario mode"), "屏幕模式": ("screen.mode", "screen mode"), "屏幕亮度": ("screen.brightness", "screen brightness"),
      "电动遮阳帘": ("device.sunshade", "sunshade")}
for kind in meta:
    for zh, m in meta[kind].items():
        if zh in EN: m["id"], m["en"] = EN[zh]
vocab = {"_note": "座舱原子能力 v2，来自公司 2026-07 能力表（notes/inputs/座舱原子能力-最新.xlsx），由 import_capabilities.py 生成；旧表见 vocab_v1.json。",
         "conditions": conditions, "actions": actions, "meta": meta,
         "safety_must_not": [{"primary": "低速行人警报音", "secondary_any": ["关闭"], "reason": "AVAS 不允许被场景自动关闭（欧盟 R138、美国 FMVSS 141）"}],
         "removed_from_sheet": ["条件：时间区间、日期区间、温度控制、风量、出风模式、香氛类型与浓度、温区同步、导航状态、预计到达时间、预计到达距离、多媒体播放中、电动遮阳帘开度"]}
json.dump(vocab, open(os.path.join(HERE, "vocab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("conditions", len(conditions), "actions", len(actions))
print("maturity:", Counter(m["maturity"] for k in meta for m in meta[k].values()))
