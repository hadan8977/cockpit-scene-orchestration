# 评分器和调度器快照

用于 p9/p10/p11 阶段及最终回归。文本换行统一为 LF，与这些运行 manifest 的哈希口径相同。01—03 的调度器 safe_eval.py 可从提交 54af348 取得；评分器和能力文件未变。04_protocol 的调度器精确中间版本未单独保存，其 manifest 哈希仍保留，原始响应和相同版本评分器足以重新计算质量结果；不声称已恢复该中间调度器的字节。

2026-09-07 的 p12 运行在173条后发生 Windows 文件共享锁错误。只修改 safe_eval.atomic 的本地 os.replace 重试，保存新实现为 safe_eval.after-io-retry.py；原 safe_eval.py 未改动，用于复现历史哈希。05d_p12_language/manifest.before-io-retry.json 和 io-amendment.json 记录修订前后哈希。模型调用、评分器、prompt、题集与参数不变。


p13及最终验收沿用safe_eval.after-io-retry.py对应实现。原匿名评审执行源码保存在blind_review.before-parser-fix.py；7个缺preference的响应按JUDGE-PARSER-AMENDMENT.md离线恢复原始四维评分，未重跑。
