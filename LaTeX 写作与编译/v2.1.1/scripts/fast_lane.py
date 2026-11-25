r"""fast_lane.py — 最小闭环保底管线（v2.1.1 增量，本版唯一机制改动）。

一条命令跑完"保底闭环"：init_result → inspect_case → tex_build(fastlane 单轮)
→ tex_logscan → tex_check → assemble_result(partial) → validate_output。
设计目的： Harness 预算（64 请求/900 秒/3 案例）下，**第一个模型请求之后
/app/output 就存在合法 partial 产物**；之后 Agent 再按 SKILL.md 细流程迭代增强，
任何时刻中断都有可评结果。

用法:
  python3 fast_lane.py [--case /input/case.json] [--task /input/task.md]
      [--input-dir /input] [--work /app/work] [--out /app/output]
      [--skill "name vX"] [--dir <skill根目录>]

参数读自 direction.json 的 fast_lane 节（enabled/compile_timeout/passes，
参数真被读取）。每步失败不中止后续步骤，全部异常落 work/exceptions.json。
仅标准库；整管线典型耗时 = 一轮编译时间（<120s）。
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def load_params(skill_dir):
    d = {"enabled": True, "compile_timeout": 90, "passes": 2, "until_converge": False}
    try:
        user = (json.load(open(os.path.join(skill_dir, "direction.json"),
                             encoding="utf-8")).get("fast_lane") or {})
        d.update({k: v for k, v in user.items() if k in d})
    except Exception:
        pass
    return d


def run_step(name, cmd, log, timeout=150):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, timeout=timeout, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.stdout.decode("utf-8", "replace")
        log.append({"step": name, "rc": p.returncode,
                    "seconds": round(time.time() - t0, 2),
                    "tail": out.strip().splitlines()[-3:] if out.strip() else []})
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        log.append({"step": name, "rc": -9, "seconds": round(time.time() - t0, 2),
                    "tail": [f"超时(>{timeout}s)"]})
        return False
    except OSError as e:
        log.append({"step": name, "rc": -1, "seconds": round(time.time() - t0, 2),
                    "tail": [str(e)]})
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--skill", default="latex-template-reproducible-build v2.1.1")
    ap.add_argument("--dir", default=os.path.dirname(HERE))
    args = ap.parse_args()

    P = load_params(args.dir)
    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    log = []
    py = sys.executable

    def S(script):
        return os.path.join(HERE, script)

    # 1 保底骨架（必须先于一切）
    run_step("init_result", [py, S("init_result.py"), "--case", args.case,
                             "--out", args.out], log)
    # 2 侦察+暂存
    run_step("inspect_case", [py, S("inspect_case.py"), "--case", args.case,
                              "--task", args.task, "--input-dir", args.input_dir,
                              "--work", args.work], log)
    # 3 单轮编译（fastlane 标签，限轮次）
    bcmd = [py, S("tex_build.py"), "--project", os.path.join(args.work, "project"),
            "--work", args.work, "--tag", "fastlane",
            "--timeout", str(P["compile_timeout"]), "--passes", str(P["passes"])]
    if P["until_converge"]:
        bcmd.append("--until-converge")
    run_step("tex_build", bcmd, log, timeout=P["compile_timeout"] * (P["passes"] + 2))
    # 4 日志分诊 + 源码审查（诊断信息入 reports，不阻塞）
    run_step("tex_logscan", [py, S("tex_logscan.py"), "--work", args.work, "--top", "10"], log)
    run_step("tex_check", [py, S("tex_check.py"), "--work", args.work], log)
    # 5 组装 partial（即使编译失败也交付诊断与工程现状）
    run_step("assemble", [py, S("assemble_result.py"), "--work", args.work,
                          "--out", args.out, "--case", args.case,
                          "--skill", args.skill, "--status", "partial"], log)
    # 6 闸门
    run_step("validate", [py, S("validate_output.py"), "--out", args.out,
                          "--case", args.case], log)

    lane = {"params": P, "steps": log,
            "ok_steps": sum(1 for s in log if s["rc"] == 0),
            "total_seconds": round(sum(s["seconds"] for s in log), 2),
            "note": "保底闭环完成；/app/output 已存在合法 partial，可继续细流程增强。"}
    with open(os.path.join(args.work, "fast_lane_log.json"), "w", encoding="utf-8") as f:
        json.dump(lane, f, ensure_ascii=False, indent=2)

    print(f"[fast_lane] 步骤={len(log)} 成功={lane['ok_steps']} "
          f"耗时={lane['total_seconds']}s → /app/output 保底 partial 已落盘")
    for s in log:
        mark = "OK " if s["rc"] == 0 else f"rc={s['rc']}"
        tail = s["tail"][-1][:90] if s["tail"] else ""
        print(f"  [{mark}] {s['step']} ({s['seconds']}s) {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
