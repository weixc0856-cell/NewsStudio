# Stage 2（ep31 起）

- 新期档案命名：`epNN-<slug>.md`（从 `ep31` 开始），正文用 `../_template.md`。
- 制作完成后：
  1. 在仓库根目录 `episodes_registry.json` 的 `episodes` 数组**追加一条**记录
     （`id / title / core_entity / event / url / tags`），不要重写整个文件；
  2. 在 `../制作记录-按期归档.md` 追加该期记录；
  3. 更新 `../../专栏策划-AI时代的基建.md` 的期数与阶段入口；
  4. 不需要修改 `stage1/` 下的任何文件。
- 查重时只读 registry；同一 `core_entity` 允许再做，但 `event` 与 `tags` 必须不同。
