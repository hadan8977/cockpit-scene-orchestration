#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD v17 配图：重画口径变化的图。输出 docs/media-v17/"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from diagram import Diagram, NODE_FILL

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "media-v17")
os.makedirs(OUT, exist_ok=True)


def fig1_product():
    """图 1 产品级关系：四个入口、一道判断、生成、四种呈现、场景引擎；条件触发是场景引擎的既有能力"""
    D = Diagram(2000, 980)
    D.group(40, 60, 300, 720, "四个入口：车怎么知道该考虑布置场景")
    D.node("explicit", 190, 170, "显式语音\n「做一个雨夜回家的场景」", w=250, h=90)
    D.node("state", 190, 320, "状态表达\n「她还要二十分钟」", w=250, h=90)
    D.node("obs", 190, 470, "观察\n连续几晚同一串操作", w=250, h=90)
    D.node("save", 190, 620, "顺手存\n长按控件「记住现在这样」", w=250, h=90)

    D.node("gate", 620, 395, "要不要出手\n显著性 + 三问 + 负面记忆 + 打扰额度", w=300, h=120, kind="diamond")
    D.node("silent", 620, 560, "沉默，不进任何队列", w=240, h=60, kind="grey")
    D.node("brain", 1000, 320, "场景大脑 一次调用\n生成建议对象\n（先查已有场景：新建 / 并入）", w=290, h=110)
    D.node("verifier", 1000, 500, "验证器\n闭集、安全值、注入", w=220, h=80)
    D.node("present", 1360, 320, "呈现调度 四种形式\n顺手提示 / 一句话询问 / 试演三秒 / 一句话改一处", w=300, h=110)
    D.node("myscenes", 1360, 600, "「我的场景」\n用户保存的场景 + 官方情景模式", w=300, h=90, kind="green")
    D.node("confirm", 1000, 700, "动作清单确认\n默认全选，可裁剪", w=240, h=80)

    D.group(1120, 700, 840, 260, "场景引擎（既有能力，不是入口）")
    D.node("trigger", 1290, 815, "条件触发\n时间线执行、谢幕", w=250, h=90, kind="green")
    D.node("guard", 1290, 915, "出厂守护清单（出厂规则）", w=250, h=54, kind="green", small=True)
    D.node("engine", 1650, 850, "场景引擎 单点执行\n执行前快照，一键恢复", w=270, h=100)

    D.node("feedback", 1780, 160, "反馈\n记忆、账本、埋点", w=220, h=90)

    D.edge("explicit", "brain", label="直达，不经判断", route=[(500, 170), (800, 170)], label_pos=0.5)
    D.edge("state", "gate", sides=("r", "l"), label="", label_pos=0.5)
    D.edge("obs", "gate", sides=("r", "l"), label="先过显著性", label_pos=0.45)
    D.edge("gate", "silent", label="任一否决", sides=("b", "t"))
    D.edge("gate", "brain", label="通过", sides=("r", "l"), label_pos=0.45)
    D.edge("brain", "verifier", sides=("b", "t"))
    D.edge("verifier", "present", route="hv", sides=("r", "b"), label="建议对象", label_pos=0.35)
    D.edge("present", "engine", label="用户说「好」：应用一次", route=[(1650, 320)], sides=("r", "t"), label_pos=0.5, label_shift=(-30, 0))
    D.edge("present", "myscenes", label="用户说「存」或「就这样」", sides=("b", "t"), label_pos=0.5, label_shift=(150, 0))
    D.edge("save", "confirm", route="hv", sides=("r", "t"), label="", label_pos=0.5)
    D.edge("confirm", "myscenes", route="hv", sides=("r", "b"), label="", label_pos=0.3)
    D.edge("myscenes", "trigger", label="条件满足自动执行", route="hv", sides=("b", "t"), label_pos=0.5)
    D.edge("trigger", "engine")
    D.edge("guard", "engine", sides=("r", "l"))
    D.edge("engine", "feedback", sides=("t", "b"))
    D.edge("feedback", "gate", style="dotted", route=[(1780, 50), (620, 50)], sides=("t", "t"), label="下次判断前拉取，非实时", label_pos=0.5)
    D.save(os.path.join(OUT, "fig01-product-overview.png"))


def fig4_nonvoice():
    """图 4 非语音入口的技术路径：观察在车端完成；顺手存就地保存；场景引擎条件触发是既有能力"""
    D = Diagram(2000, 900)
    # 观察
    D.group(30, 40, 1180, 330, "观察入口：挖掘与判断都在车端，候选达标才上云")
    D.node("ops", 150, 190, "手动操作序列\n车辆与环境状态\n舱内感知（只用事件）", w=240, h=130)
    D.node("mine", 410, 190, "车端挖掘\n空闲时，每日一次\n条件 + 动作集合", w=200, h=110)
    D.node("shadow", 640, 190, "影子模式\n只记不执行\n最多 7 天", w=180, h=110)
    D.node("match", 890, 190, "查我的场景\n新建 / 并入", w=240, h=130, kind="diamond")
    D.node("gate", 1100, 190, "显著性\n+ 三问", w=170, h=110, kind="diamond")
    D.edge("ops", "mine"); D.edge("mine", "shadow"); D.edge("shadow", "match", label="重合达标", label_pos=0.5)
    D.edge("match", "gate", label="", label_pos=0.5)
    D.node("drop", 640, 320, "不达标：丢弃", w=180, h=44, kind="grey", small=True)
    D.edge("shadow", "drop", sides=("b", "t"))

    # 顺手存
    D.group(30, 420, 1180, 220, "顺手存：就地保存，不经判断，不上云也能存")
    D.node("press", 150, 535, "长按控件\n「记住现在这样」", w=220, h=90)
    D.node("confirm", 440, 535, "动作清单确认\n只列最近 10 分钟改过的项\n默认全选，可裁剪", w=280, h=110)
    D.node("name", 780, 535, "命名与条件\n在线由场景大脑命名，离线用默认名\n默认无自动触发，可勾条件", w=340, h=120)
    D.edge("press", "confirm"); D.edge("confirm", "name")

    # 云端生成与呈现
    D.node("brain", 1400, 190, "场景大脑\n补理解与命名\n（并入时生成增量）", w=220, h=110)
    D.node("verifier", 1660, 190, "验证器", w=140, h=70)
    D.node("present", 1880, 190, "呈现调度\n顺手提示起步", w=190, h=90)
    D.edge("gate", "brain", label="候选达标", label_pos=0.5)
    D.edge("brain", "verifier"); D.edge("verifier", "present")

    D.node("myscenes", 1400, 535, "「我的场景」\n用户保存的场景 + 官方情景模式", w=300, h=90, kind="green")
    D.edge("name", "myscenes", label="保存")
    D.edge("present", "myscenes", label="用户说「存」", route="vh", sides=("b", "t"), label_pos=0.5)

    # 场景引擎（既有）
    D.group(30, 660, 1940, 220, "场景引擎（既有能力）：条件触发、时间线、谢幕；出厂守护清单是出厂规则")
    D.node("trigger", 400, 780, "条件触发\n时段、位置、天气、行程事件\n由条件语义层算出", w=320, h=100, kind="green")
    D.node("guard", 900, 780, "出厂守护清单\n只含 A 级单动作，停车或离车态", w=320, h=100, kind="green")
    D.node("engine", 1400, 780, "场景引擎 单点执行\n快照、时间线、谢幕", w=300, h=100)
    D.node("write", 1800, 780, "回写\n记忆、账本、埋点", w=220, h=100)
    D.edge("myscenes", "trigger", route=[(1400, 640), (400, 640)], sides=("b", "t"), label="条件满足自动执行", label_pos=0.6)
    D.edge("trigger", "engine"); D.edge("guard", "engine"); D.edge("engine", "write")
    D.save(os.path.join(OUT, "fig04-nonvoice-paths.png"))


def fig7_observation():
    """图 7 观察入口：从操作到候选到顺手提示，含判别"""
    D = Diagram(2000, 560)
    D.node("a", 150, 120, "手动操作序列\n灯、温、座椅、音乐、车窗、声场", w=250, h=90)
    D.node("b", 150, 280, "车辆与环境状态\n时段、位置、星期类型、安全带、车锁", w=250, h=90)
    D.node("c", 150, 440, "舱内感知\n只用事件，不存画面", w=250, h=90)
    D.node("mine", 480, 280, "车端挖掘\n空闲时每日一次\n记「条件 + 动作集合」", w=230, h=110)
    D.node("cand", 770, 280, "候选\n14 天内 3 次以上\n一致率七成、动作 2 个以上", w=250, h=110)
    D.node("shadow", 1060, 280, "影子模式\n只记不执行，最多 7 天\n重合度达标才继续", w=250, h=110)
    D.node("match", 1360, 280, "查「我的场景」\n条件重合、动作重合", w=230, h=130, kind="diamond")
    D.node("gate", 1660, 160, "要不要出手三问", w=210, h=70)
    D.node("nudge", 1660, 60, "顺手提示（建议为主语）\n「要不要把这几步存成到家？」", w=300, h=70, small=True)
    D.node("extend", 1660, 330, "增量建议\n「到家场景加一项：座椅加热？」", w=300, h=80)
    D.node("drop", 1360, 470, "不达标：静默丢弃", w=220, h=50, kind="grey", small=True)
    for s in ("a", "b", "c"):
        D.edge(s, "mine")
    D.edge("mine", "cand"); D.edge("cand", "shadow"); D.edge("shadow", "match")
    D.edge("match", "gate", label="新建", route="hv", sides=("r", "l"), label_pos=0.5)
    D.edge("gate", "nudge", sides=("t", "b"))
    D.edge("match", "extend", label="并入已有场景", route="hv", sides=("r", "l"), label_pos=0.5)
    D.edge("shadow", "drop", route="vh", sides=("b", "l"), label="", label_pos=0.5)
    D.note(1660, 450, "证据只在用户点「为什么」时展示，\n不主动念出「我看到你…」", w=320)
    D.save(os.path.join(OUT, "fig08-observation.png"))


def fig8_lifecycle():
    """图 8 场景生命周期"""
    D = Diagram(2000, 600)
    D.node("birth", 170, 300, "出生\n带来源标记：语音创建、\n观察学习、顺手存、模板改", w=280, h=120)
    D.node("trial", 470, 300, "首次应用\n试演三秒", w=180, h=90)
    D.group(600, 170, 560, 260, "使用中")
    D.node("saved", 880, 250, "用户保存的场景\n条件满足即执行（既有能力）", w=460, h=70, kind="green")
    D.node("sugg", 880, 360, "车提出、尚未保存的建议\n按主动程度 L1 → L2，说「存」即成场景", w=460, h=70)
    D.node("health", 1400, 200, "健康监测", w=200, h=110, kind="diamond")
    D.node("freeze", 1760, 120, "异常率超阈值：冻结", w=260, h=60)
    D.node("archive_hint", 1760, 260, "长期未触发：提示归档", w=260, h=60)
    D.node("expire", 1420, 420, "到期归档\n季节性与事件性，可一键复活", w=320, h=80)
    D.node("tomb", 1460, 540, "墓碑\n被撤销或删除，进负面记忆，同类不再起", w=440, h=80)
    D.edge("birth", "trial"); D.edge("trial", "saved", sides=("r", "l"))
    D.edge("trial", "sugg", route="vh", sides=("b", "l"), label="", label_pos=0.5)
    D.edge("sugg", "saved", sides=("t", "b"), label="「存」", label_pos=0.5, label_shift=(80, 0))
    D.edge("saved", "health", route="hv", sides=("r", "l"), label="", label_pos=0.5)
    D.edge("health", "freeze", route="hv", sides=("t", "l")); D.edge("health", "archive_hint", sides=("r", "l"))
    D.edge("saved", "expire", route=[(1170, 250), (1170, 420)], sides=("r", "l"))
    D.edge("saved", "tomb", route=[(1200, 250), (1200, 540)], sides=("r", "l"))
    D.save(os.path.join(OUT, "fig09-lifecycle.png"))


def fig9_e2e():
    """图 9 端到端实现路径"""
    D = Diagram(2000, 700)
    D.node("nlu", 140, 90, "语义理解\n场景域与布景分\n处境 / 情绪 / 生理判定", w=250, h=100)
    D.node("mem", 140, 230, "记忆包\n不超 300 token，负面优先", w=250, h=80)
    D.node("scenes", 140, 360, "已有场景摘要\n最相关的 3 条", w=250, h=80)
    D.node("prompt", 420, 230, "提示词渲染\n自注册表生成", w=200, h=90)
    D.node("model", 650, 230, "云端小模型\n一次调用", w=180, h=90)
    D.node("cd", 870, 230, "约束解码\n闭集 schema", w=180, h=90)
    D.node("ver", 1110, 230, "验证器\n安全、行驶、话长\n注入、成熟度档位、场景引用", w=250, h=110)
    D.node("obj", 1360, 230, "建议对象\n含 relation：新建 / 并入", w=210, h=90)
    D.node("present", 1600, 230, "呈现调度\n四种形式", w=180, h=90)
    D.node("exec", 1600, 430, "执行策略\n再查注册表、同时命中仲裁\n快照、熔断 2.5 秒", w=300, h=100)
    D.node("engine", 1600, 600, "场景引擎\n300 毫秒", w=180, h=80)
    D.node("write", 1860, 600, "回写\n记忆、账本、埋点", w=200, h=80)
    D.node("gate", 650, 460, "评测门\n134 题、8 道注入\n双路体验门", w=400, h=150, kind="diamond")
    for a in ("nlu", "mem", "scenes"):
        D.edge(a, "prompt")
    D.edge("prompt", "model"); D.edge("model", "cd"); D.edge("cd", "ver"); D.edge("ver", "obj"); D.edge("obj", "present")
    D.edge("present", "exec", sides=("b", "t"), label="用户同意", label_pos=0.5)
    D.edge("exec", "engine", sides=("b", "t")); D.edge("engine", "write")
    D.edge("gate", "ver", style="dotted", label="不过不上线", route="hv", sides=("r", "b"), label_pos=0.4)
    D.save(os.path.join(OUT, "fig10-e2e.png"))


def fig_merge():
    """新图：新建还是并入的判别，与多场景同时命中的让步"""
    D = Diagram(2000, 760)
    D.group(30, 30, 1230, 700, "判别：候选场景与「我的场景」逐条比对")
    D.node("cand", 170, 380, "候选场景\n来自观察 / 显式创建保存时 /\n状态表达命中", w=250, h=110)
    D.node("q1", 470, 380, "条件相同或\n被已有场景包含？", w=250, h=140, kind="diamond")
    D.node("q2", 800, 220, "动作重合\n不少于一半？", w=230, h=130, kind="diamond")
    D.node("q3", 800, 560, "触发时刻\n会重叠？", w=230, h=130, kind="diamond")
    D.node("extend", 1090, 120, "并入：增量修改建议\n「到家场景加一项：座椅加热？」", w=300, h=90, kind="green")
    D.node("modify", 1090, 300, "并入：改值或加条件分支\n「夜里 10 点后灯改 15%？」", w=300, h=90, kind="green")
    D.node("new_overlap", 1090, 480, "新建，标记「触发重叠」\n首次同时命中时事后一句", w=300, h=90)
    D.node("new", 1090, 650, "新建场景", w=300, h=70)
    D.edge("cand", "q1"); D.edge("q1", "q2", label="是", route="vh", sides=("t", "l"), label_pos=0.5)
    D.edge("q1", "q3", label="否", route="vh", sides=("b", "l"), label_pos=0.5)
    D.edge("q2", "extend", label="是，且无冲突", route="hv", sides=("t", "l"), label_pos=0.6)
    D.edge("q2", "modify", label="有同元素不同值", route="hv", sides=("r", "l"), label_pos=0.5)
    D.edge("q2", "new_overlap", label="否", route=[(940, 220), (940, 480)], sides=("r", "l"), label_pos=0.3)
    D.edge("q3", "new_overlap", label="会", route="hv", sides=("t", "l"), label_pos=0.6)
    D.edge("q3", "new", label="不会", route="hv", sides=("b", "l"), label_pos=0.6)

    D.group(1300, 30, 670, 700, "同时命中：谁让步")
    D.node("g1", 1635, 130, "1 出厂守护清单\n安全动作先做，不合并", w=560, h=70, kind="green")
    D.node("g2", 1635, 250, "2 语音车控\n用户此刻说的指令压过一切自动动作", w=560, h=70)
    D.node("g3", 1635, 380, "3 用户保存的场景之间\n冲突元素：条件更具体者赢；\n不冲突元素合并执行；话合成一句", w=560, h=100)
    D.node("g4", 1635, 520, "4 车提出的建议\n执行中新建议转收件箱，不插队", w=560, h=70)
    D.node("g5", 1635, 640, "首次出现冲突：事后一句 + 提示合并\n用户可在「我的场景」设优先", w=560, h=70, kind="grey")
    D.edge("g1", "g2", sides=("b", "t")); D.edge("g2", "g3", sides=("b", "t")); D.edge("g3", "g4", sides=("b", "t")); D.edge("g4", "g5", sides=("b", "t"))
    D.save(os.path.join(OUT, "fig06-merge-arbitration.png"))


def fig12_demo():
    """图 12 demo 三条旅程"""
    D = Diagram(2000, 760)
    rows = [
        ("旅程一「一个傍晚」：状态表达与分寸", 110, [
            "热死了\n归车控开 MAX AC", "堵车烦死了\n问一止步，沉默", "别吵醒他\n声场切前排", "英文一句\n同路径",
            "她还要二十分钟\n答完后 L1 询问", "好啊\n试演三秒", "灯再暗点\n只改一处", "副驾门开\n谢幕", "锁车窗开着\n守护清单关窗", "收件箱\n多一条，不自动存"]),
        ("旅程二「周六造一个场景」：显式直达与硬约束", 340, [
            "做一个雨夜回家\n半秒出理解句", "关行人警报音\n法规不允许", "车窗开一半\n改成一小缝", "放我的播客\n只换声", "就这样\n查重后保存",
            "下线香氛\n热更新变灰", "下周三雨夜\n时间线执行、谢幕", "进入露营模式\n点名即调", "露营来点 K 歌\n预设上加一件事", "冬天开座椅加热\n日期区间"]),
        ("旅程三「四个晚上」：观察到保存，透明可删", 570, [
            "四晚手动调灯\n挖掘 + 影子", "第四晚调灯\n顺手提示「存成到家？」", "存\n成为我的场景", "下周一到家\n自动执行，首次试演",
            "又学到座椅加热\n并入：加一项？", "它学会了什么\n删一条负规则", "说不用\n7 天沉默", "导入夹带注入\n验证器拦下", "指标面板\n采纳率、打扰率", "未来一瞥\nL3 / L4 暂缓"]),
    ]
    for title, y, beats in rows:
        D.group(20, y - 90, 1960, 190, title)
        x = 120
        prev = None
        for i, b in enumerate(beats):
            nid = f"{y}-{i}"
            kind = "grey" if "未来一瞥" in b else "box"
            D.node(nid, x, y + 15, b, w=176, h=90, small=True, kind=kind)
            if prev:
                D.edge(prev, nid)
            prev = nid
            x += 195
    D.save(os.path.join(OUT, "fig13-demo-journeys.png"))


if __name__ == "__main__":
    fig1_product(); fig4_nonvoice(); fig7_observation(); fig8_lifecycle(); fig9_e2e(); fig_merge(); fig12_demo()
