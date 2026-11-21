# 全城道路证据集 · R6.2

`catalog.json`是本批唯一发布目录，含84条证据记录、339实体覆盖核对、60条新旧记录关系和13项排除／参照说明。原R6.1的21条来源记录继续单独保留；统计总数不表示独立古代道路数量。

- `sources/road-source-audit.json`：9个来源、9组局部约束、原件访问与图例审查。
- `sources/frames.json`：本批5幅独立来源图框的出处、尺寸、哈希、分期与限制。
- `sources/yongxiang-arrows.json`：唯一新增像素读点，6段方向箭杆，性质为来源图示意，不是实测路缘。
- `sources/textual-readings-supplement.json`：乐里道句读与三处北廊门道的独立证据。
- `atlas.css`、`atlas.js`：本批独立页面的呈现与交互。

原图在来源发布页查看，本目录记录原文件名、哈希和已核图例，不镜像整篇来源文章。局部JSON Pointer均指向仓库中的已核资料；`geometry_refs.native_geometry`逐值保存该指针的原始数据，不能从页面排版反算古坐标。

完成现有站点全链构建及 `tools/road_location_atlas.py` 后，运行：

```sh
python tools/all_road_atlas_r62.py
python -m unittest discover -s tests -p 'test_prosperity_all_road_atlas_r62.py' -v
python tests/browser_all_road_atlas_r62.py
```

发布及正式站验收遵循仓库 `AGENTS.md`。研究说明见[roads-r62-research.md](../../docs/roads-r62-research.md)。
