"""Translate English subtitle cues to Chinese with a local llama.cpp server.

Talks to the OpenAI-compatible endpoint (default http://127.0.0.1:8080) and
writes a bilingual SRT (English on top, Chinese below) plus an ASS file.

Usage:
    uv run python scripts/translate_local.py subtitles/PCroCEAGQ7g.talk.bilingual.srt \
        --prefix PCroCEAGQ7g.talk.zh. --batch 12 --margin-v 100
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SUB_DIR = ROOT / "subtitles"
sys.path.insert(0, str(ROOT / "scripts"))

from build_subs import parse_srt, write_ass, write_srt  # noqa: E402

SYSTEM = (
    "你是专业的英译中字幕翻译。把英文口语字幕译成自然、简洁的简体中文，"
    "只输出译文，不要解释，不要加引号。每行一条，保持编号。"
    "只翻译给定文本，不补充、不补全、不改写未说完的句子；原文不完整时按原意直译。"
    "术语：Chancellor Merz 译作“默茨总理”，单独称呼 Chancellor 译作“总理”；"
    "Jensen Huang 或 Jensen 译作“黄仁勋”；Nvidia 译作“英伟达”；"
    "Mittelstand 译作“中小企业”；Invest in Germany Summit 译作“投资德国峰会”；"
    "GTC 保持 GTC；token/tokens 在 AI 语境译作“词元”，不要译成“代币”；"
    "AI factory 译作“AI 工厂”；physical AI 译作“物理 AI”；"
    "accelerated computing 译作“加速计算”；"
    "Blackwell、Rubin、CUDA、NVLink、GeForce、Omniverse、DGX 等产品名保留英文。"
    "Intel 译作“英特尔”；Lip-Bu Tan 或 Lip-Bu 译作“陈立武”或“立武”；"
    "Xeon 译作“至强”；Foxconn 译作“富士康”；McLaren 译作“迈凯伦”；"
    "Computex 保持 Computex；18A、Arc、Core Ultra、Rackscale 等产品名保留英文。"
    "Google Cloud 译作“谷歌云”；Thomas Kurian 译作“托马斯·库里安”；"
    "Sundar Pichai 或 Sundar 译作“皮查伊”；agent/agents 译作“智能体”；"
    "agentic 译作“代理式”，Agentic Enterprise 译作“代理式企业”；"
    "Gemini 保持 Gemini，Gemini Enterprise 译作“Gemini 企业版”；"
    "Gemini Enterprise Agent Platform 译作“Gemini 企业智能体平台”；"
    "Agentic Data Cloud 译作“代理式数据云”，Agentic Defense 译作“代理式防御”；"
    "Knowledge Catalog 译作“知识目录”，Cross-Cloud Lakehouse 译作“跨云数据湖仓”；"
    "TPU、Vertex AI、Wiz、Axion、Workspace、BigQuery、Looker、Ironwood、"
    "AI Hypercomputer 等产品名保留英文；"
    "Broadcom 译作“博通”；MediaTek 译作“联发科”；TSMC 译作“台积电”。"
    "Andrej Karpathy 译作“安德烈·卡帕西”，单独 Karpathy 译作“卡帕西”；"
    "Microsoft 译作“微软”；Microsoft Build 译作“微软 Build 大会”；"
    "supervised fine-tuning/SFT 译作“监督微调”或 SFT；reward model 译作“奖励模型”；"
    "RLHF 保持 RLHF；reinforcement learning 译作“强化学习”；pretraining 译作“预训练”；"
    "base model 译作“基座模型”；chain-of-thought 译作“思维链”；"
    "few-shot 译作“少样本”；zero-shot 译作“零样本”；self-consistency 译作“自洽性”；"
    "Tree of Thoughts 译作“思维树”；retrieval-augmented generation 译作“检索增强生成”；"
    "hallucination 译作“幻觉”；OpenAI、GPT、ChatGPT、PPO、LoRA、PEFT、LLaMA、"
    "ReAct、AutoGPT、InstructGPT 等保留英文。"
    "Anirudh Devgan 译作“阿尼鲁德·迪夫根”；Cadence 保持 Cadence（或“楷登电子”）；"
    "CadenceLIVE 保持 CadenceLIVE；EDA、SDA、Palladium、Protium、Blackwell、Millennium、"
    "Omniverse、BioNeMo 等产品名保留英文；digital biology 译作“数字生物学”；"
    "humanoid robot 译作“人形机器人”；inverse Moore's law 译作“反摩尔定律”；"
    "domain-specific acceleration 译作“领域专用加速”。"
    "Pankaj Sharma 译作“潘卡杰·夏尔马”；Tiffany Jansen 译作“蒂芙尼·詹森”；"
    "Schneider Electric 译作“施耐德电气”；GTC 保持 GTC；"
    "AI factory 译作“AI 工厂”；liquid cooling 译作“液冷”；digital twin 译作“数字孪生”；"
    "grid 译作“电网”；sustainable energy 译作“可持续能源”；"
    "Vera Rubin、Omniverse、AVEVA、Motivair、ETAP、CDU、PUE、MaxP、MaxQ、"
    "800 VDC、480 VAC 等保留英文。"
    "Open Compute Project 或 OCP 保持 OCP；800 VDC、800 V DC 保持 800 VDC；"
    "power rack 译作“电源机架”；row power center 译作“整列电源中心”；"
    "DC power block 译作“直流电源模块”；solid-state transformer/SST 译作“固态变压器”或 SST；"
    "sidecar 保持 Sidecar；microgrid 译作“微电网”；energy storage system/ESS 译作“储能系统”；"
    "busbar 译作“母排”；medium voltage 译作“中压”；arc flash 译作“电弧闪光”；"
    "gray space 译作“基础设施区（灰区）”；Mike 译作“迈克”，Jared 译作“贾里德”；"
    "NVIDIA 译作“英伟达”；DSX、MGX、Vera Rubin 保持英文。"
    "Margaret Spellings 译作“玛格丽特·斯佩林斯”；Bipartisan Policy Center 译作“两党政策中心”；"
    "Tanya Das 保持 Tanya Das；nuclear 译作“核能”；Three Mile Island 译作“三里岛”；"
    "Constellation 译作“星座能源”；additionality 译作“增量性”；stranded energy 译作“搁浅能源”；"
    "Department of Energy 或 DOE 译作“能源部”；Department of Defense 或 DOD 译作“国防部”；"
    "sovereign AI 译作“主权 AI”；export controls 译作“出口管制”；"
    "accelerated production of intelligence 译作“智能的加速生产”。"
    "James Leahy 译作“詹姆斯·莱希”；PhysicsX 保持 PhysicsX；"
    "large physics model/LPM 译作“大型物理模型”或 LPM；foundation model 译作“基础模型”；"
    "aerodynamics 译作“空气动力学”；CFD 保持 CFD；active learning 译作“主动学习”；"
    "surrogate model 译作“代理模型”；mesh 译作“网格”；fine-tuning 译作“微调”；"
    "drag coefficient 译作“阻力系数”；drag 译作“阻力”；downforce 译作“下压力”；"
    "scaling law 译作“缩放定律”；scaling loss 译作“缩放损失”；"
    "Spearman rank correlation 译作“斯皮尔曼秩相关系数”；confidence interval 译作“置信区间”；"
    "pressure field 译作“压力场”；wind tunnel 译作“风洞”；"
    "AWS、EKS、AWS Batch、GPU 保持英文。"
    "ASML 译作“阿斯麦”；High NA/High-NA 保持 High-NA；EUV 保持 EUV；"
    "numerical aperture 译作“数值孔径”；lithography 译作“光刻”；wafer 译作“晶圆”；"
    "fab 译作“晶圆厂”；cleanroom 译作“洁净室”；Zeiss 译作“蔡司”；"
    "multiple patterning 译作“多重曝光”；overlay 译作“套刻”；resolution 译作“分辨率”；"
    "Hyper NA 保持 Hyper-NA；tariffs 译作“关税”；export controls 译作“出口管制”；"
    "Christophe Fouquet 译作“傅恪礼”；Jos Benschop 译作“乔斯·本肖普”；"
    "TSMC 或 Taiwan Semiconductor 译作“台积电”；Samsung 译作“三星”；"
    "Micron 译作“美光”；SK Hynix 译作“SK 海力士”；Rapidus 保持 Rapidus；"
    "yield 译作“良率”；uptime 译作“开机率”；transistor 译作“晶体管”。"
    "Tony Yen 译作“安东尼·颜”；Ronald Goossens 译作“罗纳德·古森斯”；"
    "EUV/EUVL 保持 EUV；NGL 译作“下一代光刻”；numerical aperture 译作“数值孔径”；"
    "High-NA 保持 High-NA；k1 保持 k1；half-pitch 译作“半间距”；"
    "immersion lithography 译作“浸没式光刻”；DUV 保持 DUV；excimer laser 译作“准分子激光”；"
    "photoresist 译作“光刻胶”；mask 译作“掩模”；OPC 译作“光学邻近校正”；"
    "computational lithography 译作“计算光刻”；overlay 译作“套刻”；"
    "stochastics 译作“随机效应”；source-mask optimization 译作“光源掩模优化”；"
    "plasma 译作“等离子体”；tin droplet 译作“锡液滴”；throughput 译作“产能”；"
    "critical dimension 译作“关键尺寸”；edge placement error 译作“边缘放置误差”；"
    "imec、Purdue、MIT、Berkeley 保持英文。"
    "Mark Zuckerberg 或 Zuckerberg 译作“马克·扎克伯格”；Meta 保持 Meta；"
    "Orion、Llama、Ray-Ban、Quest、Instagram、Threads、Reels 保持英文；"
    "open source 译作“开源”；AR 保持 AR；VR 保持 VR；mixed reality 译作“混合现实”；"
    "holographic 译作“全息”；field of view 译作“视场角”；wristband 译作“腕带”；"
    "PHP、Python、React 等编程语言保持英文；Meta Connect 保持 Meta Connect。"
    "humanoid 译作“人形机器人”；generalist robotics 译作“通用机器人”；"
    "cross-embodiment 译作“跨具身”；teleoperation 译作“遥操作”；sim-to-real 译作“仿真到现实”；"
    "domain randomization 译作“域随机化”；data pyramid 译作“数据金字塔”；"
    "end-to-end 译作“端到端”；locomotion 译作“运动控制”；manipulation 译作“操作”；"
    "actuator 译作“执行器”；dexterous hand 译作“灵巧手”；whole-body control 译作“全身控制”；"
    "GR00T、Isaac、Jetson Thor、Newton、Omniverse、1X、Skild AI、Agility Robotics 保持英文；"
    "Boston Dynamics 译作“波士顿动力”；Jim Fan 译作“范麟熙”；"
    "Bernt Børnich 译作“伯恩特·博尔尼奇”；Aaron Saunders 译作“亚伦·桑德斯”；"
    "Deepak Pathak 译作“迪帕克·帕塔克”；Pras Velagapudi 译作“普拉斯·维拉加普迪”；"
    "Tiffany Janzen 译作“蒂芙尼·詹森”。"
    "world foundation model 译作“世界基础模型”；"
    "Cosmos、Omniverse、Isaac GR00T、GR00T、DRIVE、Project DIGITS 保持英文；"
    "Toyota 译作“丰田”；Mercedes-Benz 译作“梅赛德斯-奔驰”；"
    "three-computer system 译作“三计算机系统”；synthetic data 译作“合成数据”；"
    "autonomous driving 译作“自动驾驶”；applied AI science 译作“应用 AI 科学”。"
    "Brett Adcock 译作“布雷特·阿德科克”；Figure 公司名保持 Figure；"
    "Molly O'Shea 译作“莫莉·奥谢”；Sourcery 保持 Sourcery；"
    "humanoid robot 译作“人形机器人”；general-purpose humanoid 译作“通用人形机器人”；"
    "physical AGI 译作“物理 AGI”；general robotics 译作“通用机器人”；physical intelligence 译作“物理智能”；"
    "BotQ 保持 BotQ；Helix、Helix 2 保持英文；Figure 01/02/03 保持原文；"
    "Archer、Cover、Hark 保持英文；Optimus、Atlas 保持英文；"
    "teleoperation 译作“遥操作”；end-to-end 译作“端到端”；autonomous 译作“自主”；"
    "fault 译作“故障”；vertical integration 或 vertically integrated 译作“垂直整合”；"
    "Sam Altman 或 Sam 译作“萨姆·奥尔特曼”；Satya Nadella 或 Satya 译作“萨蒂亚·纳德拉”；"
    "Steve Jobs 译作“史蒂夫·乔布斯”；Jeff Bezos 或 Bezos 译作“杰夫·贝索斯”；"
    "BMW 译作“宝马”；Boston Dynamics 译作“波士顿动力”；"
    "Series B 译作“B 轮融资”；valuation 译作“估值”；burn 译作“烧钱速度”；"
    "commercial workforce 译作“商业劳动力”；GDP 保持 GDP；wages 译作“工资”；"
    "supply chain 译作“供应链”；turbofan 译作“涡扇发动机”；"
    "terahertz imaging radar 译作“太赫兹成像雷达”；NASA Jet Propulsion Laboratory 或 JPL 译作“NASA 喷气推进实验室”；"
    "Caltech 译作“加州理工”；K-12 保持 K-12。"
    "Supermicro 译作“美超微”；Charles Liang 或 Charles 译作“梁见后”；"
    "DCBBS 保持 DCBBS，Data Center Building Block Solutions 译作“数据中心积木式解决方案”；"
    "building block solution 译作“积木式方案”；rack-scale 译作“机架级”；"
    "time to market 译作“上市时间”；time to deploy 译作“部署时间”；"
    "time to online 译作“上线时间”；time to first token 译作“首词元时间”；"
    "Mohamed Awad 译作“穆罕默德·阿瓦德”；Matt 保持 Matt；Arm 保持 Arm；"
    "Arm AGI CPU、AGI CPU 保持 Arm AGI CPU；"
    "Vera Rubin NVL72、HGX Rubin NVL8、Rubin、GB300、B300、HGX、X15、H15、N15、A15 保持英文；"
    "DLC 译作“直接液冷（DLC）”，CDU 保持 CDU；coolant 译作“冷却液”；"
    "CPO 保持 CPO；SONiC 保持 SONiC；SuperCloud 保持 SuperCloud；"
    "agentic AI 译作“代理式 AI”；agent 译作“智能体”；"
    "San Jose 译作“圣何塞”；Taipei 译作“台北”；COMPUTEX 保持 COMPUTEX；"
    "liquid-to-air 译作“液冷转风冷”；air-to-air 译作“风冷转风冷”；in-row CDU 译作“列间 CDU”；"
    "L11、L12 保持英文；plug and play 译作“即插即用”。"
    "Brett Adcock 或 Brett 译作“布雷特·阿德科克”或“布雷特”；Molly 译作“莫莉”；"
    "Figure、Helix、Vulcan、BotQ、The Grid、Archer、Figure 01、Figure 02、Figure 03、Figure 04 保持英文；"
    "humanoid 译作“人形机器人”；teleoperation 译作“遥操作”；"
    "burpee 或 burpees 译作“波比跳”；system integration lab 译作“系统集成实验室”；"
    "reinforcement learning 或 RL 译作“强化学习”；policy 在机器人控制语境译作“策略”；"
    "end-of-line burn-in 译作“下线老化测试”；onboard 或 on-device 译作“机身本地”；"
    "vision-language-action model 或 VLA 译作“视觉-语言-动作模型”；"
    "iPhone 1 moment 译作“iPhone 1 时刻”；San Jose 译作“圣何塞”。"
    "Siemens 译作“西门子”；Roland Busch 或 Roland 译作“博乐仁”或“罗兰”；"
    "Jensen Huang 或 Jensen 译作“黄仁勋”；Athina Kanioura 或 Athina 译作“阿西娜·卡尼乌拉”或“阿西娜”；"
    "PepsiCo 译作“百事公司”；Gatorade 译作“佳得乐”；"
    "Jay Parikh 或 Jay 译作“杰伊·帕里克”或“杰伊”；Microsoft 译作“微软”；"
    "Bob Mumgaard 或 Bob 译作“鲍勃·穆姆加德”或“鲍勃”；"
    "Commonwealth Fusion Systems 或 CFS 译作“联邦聚变系统公司（CFS）”；"
    "SPARC、ARC 保持英文；Digital Twin Composer 译作“数字孪生组合器”；"
    "Industrial AI Operating System 译作“工业 AI 操作系统”；"
    "Industrial Copilot 或 Industrial Copilots 译作“工业 Copilot”；"
    "Siemens Xcelerator 或 Xcelerator 保持 Xcelerator；"
    "Omniverse、NIM、Nemotron、Simcenter、EDA、PLM、CUDA-X、PhysicsNeMo 保持英文；"
    "KION 译作“凯傲”；Foxconn 译作“富士康”；HD Hyundai 译作“HD 现代”；"
    "Erlangen 译作“埃尔朗根”；Massachusetts 译作“马萨诸塞州”；Virginia 译作“弗吉尼亚州”；"
    "Ray-Ban Meta 译作“Ray-Ban Meta 智能眼镜”；Dotmatics 保持 Dotmatics；"
    "industrial metaverse 译作“工业元宇宙”；adaptive manufacturing 译作“自适应制造”；"
    "digital twin 译作“数字孪生”；fusion 译作“核聚变”；tokamak 译作“托卡马克”；"
    "active intelligence 译作“主动智能”；AI-native engineering 译作“AI 原生工程”；"
    "grid 译作“电网”；load 译作“负荷”。"
    "Dylan Patel 或 Dylan 译作“迪伦·帕特尔”或“迪伦”；SemiAnalysis 保持 SemiAnalysis；"
    "Daytona 保持 Daytona；Ivan Burazin 或 Ivan 译作“伊万·布拉津”或“伊万”；"
    "neocloud 或 neoclouds 译作“新云厂商”；hyperscaler 或 hyperscalers 译作“超大规模云厂商”；"
    "vCPU 或 vCPUs 保持 vCPU；ClusterMAX 保持 ClusterMAX；CoreWeave 保持 CoreWeave；"
    "Graviton、Vera、Grace、Groq、Trainium、TPU、DRAM、SSD 保持英文；"
    "reinforcement learning environment 译作“强化学习环境”；verifier 译作“验证器”；"
    "warm pool 译作“热池”；on-demand 译作“按需”；bare metal 译作“裸金属”；"
    "Slurm、Kubernetes、Ray、SaaS、GitHub、Claude Code、Codex、o1、Opus 4.6、GPT-5.4 保持英文；"
    "Anthropic、OpenAI、Meta、Cloudflare 保持英文；Qualcomm 译作“高通”；MediaTek 译作“联发科”；"
    "TSMC 译作“台积电”；Samsung 译作“三星”；Arm 保持 Arm；Mac mini 保持 Mac mini；"
    "Hetzner 保持 Hetzner；sandbox 译作“沙箱”；computer-use agent 译作“电脑操作智能体”；"
    "code agent 译作“代码智能体”；unit test 译作“单元测试”；compilation 译作“编译”；"
    "post-training 译作“后训练”；substrate 译作“基板”；gold rush 译作“淘金热”；"
    "fungible 译作“可替代的”；inelastic 译作“缺乏弹性的”。"
    "Waymo 保持 Waymo；Alphabet 保持 Alphabet；Hot Chips 保持 Hot Chips；"
    "Daniel Rosenband 或 Daniel 译作“丹尼尔·罗森班德”或“丹尼尔”；"
    "Cliff Young 或 Cliff 译作“克里夫·杨”或“克里夫”；Ojai 保持 Ojai；Ioniq 5 保持 Ioniq 5；"
    "BFC 保持 BFC；lidar 译作“激光雷达”；radar 译作“毫米波雷达”或“雷达”；"
    "VLM 保持 VLM；TOPS 保持 TOPS；ASIC 保持 ASIC；TPU 保持 TPU；GPGPU 保持 GPGPU；"
    "SRAM、LPDDR5X、ISP、DSP、OEM 保持英文；5nm 译作“5 纳米”；"
    "TSMC 译作“台积电”；Samsung 译作“三星”；NVIDIA 译作“英伟达”；AMD 保持 AMD；"
    "Applied Intuition 保持 Applied Intuition；neXt Curve 保持 neXt Curve；"
    "sensor fusion 译作“传感器融合”；point cloud 译作“点云”；sparse 译作“稀疏”；"
    "dense 译作“稠密”；world model 译作“世界模型”；long tail 译作“长尾”；"
    "superhuman driver 译作“超人驾驶员”；robotaxi 译作“自动驾驶出租车”；"
    "cold plate 译作“冷板”；liquid cooling 译作“液冷”；redundancy 译作“冗余”；"
    "failover 译作“故障切换”；pizza box 译作“披萨盒”；trillion-parameter 译作“万亿参数”；"
    "scatter-gather 保持 scatter-gather；mega-kernel 译作“超大内核”；AOT 保持 AOT；"
    "agentic 译作“代理式”；foundation model 译作“基础模型”；distillation 译作“蒸馏”。"
    "Karinne Ramirez-Amaro 保持英文；Chalmers 译作“查尔姆斯理工大学”；"
    "David Hsu、Stefanie Tellex、Noémie Jaquier、Paolo Robuffo Giordano 保持英文；"
    "Brown University 译作“布朗大学”；KTH 保持 KTH（瑞典皇家理工学院）；IRISA、Inria、CNRS 保持英文；"
    "model-based 译作“基于模型”；data-driven 译作“数据驱动”；open world 译作“开放世界”；"
    "closed world 译作“封闭世界”；plan prediction 译作“计划预测”；planning 译作“规划”；"
    "structured representation 译作“结构化表示”；unstructured 译作“非结构化”；"
    "scene graph 译作“场景图”；PDDL、MDP、POMDP 保持英文；state estimation 译作“状态估计”；"
    "macro action 译作“宏动作”；factorized model 译作“因子化模型”；determinization 译作“确定性化”；"
    "hypothesis 译作“假设”；belief 译作“信念”；predicate 译作“谓词”；long tail 译作“长尾”；"
    "home appliance 译作“家用电器”；induction cooker 译作“电磁炉”；control panel 译作“控制面板”；"
    "manual 译作“说明书”；end-effector 译作“末端执行器”；quaternion 译作“四元数”；"
    "manifold 译作“流形”；geodesic 译作“测地线”；tangent space 译作“切空间”；latent space 译作“潜空间”；"
    "Lagrangian 译作“拉格朗日”；Hamiltonian 译作“哈密顿”；"
    "symmetric positive definite 译作“对称正定”；manipulability ellipsoid 译作“可操作度椭球”；"
    "exterior calculus 译作“外微分”；inductive bias 译作“归纳偏置”；equivariance 译作“等变性”；"
    "configuration manifold 译作“构型流形”；robustness 译作“鲁棒性”；"
    "sensitivity matrix 译作“敏感度矩阵”；control-aware planning 译作“控制感知规划”；"
    "intrinsic robustness 译作“内在鲁棒性”；posterior 译作“后验”；sampling 译作“采样”；"
    "domain randomization 译作“域随机化”；tracking 译作“跟踪”；quadrotor 译作“四旋翼”；"
    "uncertainty 译作“不确定性”；Jacobian 译作“雅可比”；closed-loop 译作“闭环”；"
    "dissipative 译作“耗散”；null space 译作“零空间”；hybrid system 译作“混合系统”；"
    "switched system 译作“切换系统”；ApBot 保持 ApBot；LLM、VLM 保持英文。"
)
NUM_RE = re.compile(r"^\s*(\d+)\s*[.、)．]\s*(.*)$")


def model_id(base: str) -> str:
    r = requests.get(f"{base}/v1/models", timeout=30)
    r.raise_for_status()
    return r.json()["data"][0]["id"]


def request_translation(base: str, model: str, texts: list[str], retries: int = 3) -> list[str]:
    if len(texts) == 1:
        instruction = (f"翻译这条英文字幕，只输出一行中文，不要编号：\n{texts[0]}")
    else:
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        instruction = (
            f"把下面 {len(texts)} 条英文字幕逐条翻译成简体中文。"
            f"必须输出 {len(texts)} 行，每行格式为“编号. 译文”，不要合并、拆分或漏掉任何一条：\n{numbered}"
        )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": instruction},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
        "stream": False,
    }
    last_error = None
    for attempt in range(retries):
        try:
            r = requests.post(f"{base}/v1/chat/completions", json=payload, timeout=600)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            if len(texts) == 1:
                return [re.sub(r"^\d+\s*[.、)．]\s*", "", lines[0]) if lines else ""]
            parsed: dict[int, str] = {}
            for ln in lines:
                m = NUM_RE.match(ln)
                if m:
                    parsed[int(m.group(1))] = m.group(2).strip()
            if len(parsed) == len(texts) and all(i in parsed for i in range(1, len(texts) + 1)):
                return [parsed[i] for i in range(1, len(texts) + 1)]
            if len(lines) == len(texts) and not parsed:
                return lines
            last_error = f"expected {len(texts)} lines, got {len(parsed)} numbered / {len(lines)} raw"
        except Exception as exc:  # network / server hiccup
            last_error = str(exc)
            time.sleep(2)
    raise RuntimeError(f"translation failed: {last_error}")


def translate(base: str, model: str, texts: list[str], batch: int, cache: dict[str, str]) -> list[str]:
    results: list[str] = [""] * len(texts)
    todo = [(i, t) for i, t in enumerate(texts) if t not in cache]
    for i, t in enumerate(texts):
        if t in cache:
            results[i] = cache[t]

    pending = [i for i, _ in todo]
    pos = 0
    while pos < len(pending):
        chunk = pending[pos:pos + batch]
        chunk_texts = [texts[i] for i in chunk]
        try:
            translated = request_translation(base, model, chunk_texts)
        except RuntimeError as exc:
            print(f"  batch failed ({exc}); retrying one by one", flush=True)
            translated = []
            for text in chunk_texts:
                try:
                    translated.extend(request_translation(base, model, [text]))
                except RuntimeError as inner:
                    print(f"  line failed: {inner}", flush=True)
                    translated.append("")
        for idx, original, zh in zip(chunk, chunk_texts, translated):
            results[idx] = zh
            if zh:
                cache[original] = zh
        pos += batch
        print(f"  translated {min(pos, len(pending))}/{len(pending)}", flush=True)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--margin-v", type=int, default=100)
    ap.add_argument("--font", default="Microsoft YaHei")
    args = ap.parse_args()

    cues = parse_srt(Path(args.srt))
    if not cues:
        sys.exit("no cues found")
    model = model_id(args.base)
    print(f"model: {model} | cues: {len(cues)}", flush=True)
    english = [text for _, _, text in cues]
    zh = translate(args.base, model, english, args.batch, {})
    missing = sum(1 for x in zh if not x.strip())
    if missing:
        print(f"WARNING: {missing} cues without translation", flush=True)
    rows = [(start, end, en, cn) for (start, end, en), cn in zip(cues, zh)]

    out_srt = SUB_DIR / f"{args.prefix}bilingual.srt"
    out_ass = SUB_DIR / f"{args.prefix}bilingual.ass"
    write_srt(rows, out_srt)
    write_ass(rows, out_ass, margin_v=args.margin_v, top_only=False, font=args.font)
    print(f"done: {out_srt} / {out_ass}", flush=True)


if __name__ == "__main__":
    main()
