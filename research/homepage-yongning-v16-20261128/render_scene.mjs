/** Assemble the existing V12 scene with the imagegen-edited local raster layer.
 * No tower geometry is drawn here. The editable SVG retains both source images.
 * Usage: CODEX_PRIMARY_RUNTIME_NODE_MODULES must resolve the pinned sharp runtime.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const sharp=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES
  ? path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'sharp') : 'sharp');
const folder=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(folder,'../..');
const config=JSON.parse(await fs.readFile(path.join(folder,'scene-assembly.json'),'utf8'));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const background=await fs.readFile(path.join(folder,config.background.file));
const patch=await fs.readFile(path.join(folder,config.local_edit.file));
assert.equal(sha(background),config.background.sha256);
assert.equal(sha(patch),config.local_edit.sha256);
const baseMeta=await sharp(background).metadata(), patchMeta=await sharp(patch).metadata();
const {width,height}=config.canvas;
const {x,y,width:w,height:h}=config.local_edit.rectangle_px;
assert.equal(baseMeta.width,width); assert.equal(baseMeta.height,height);
assert.equal(patchMeta.width/patchMeta.height,w/h);
assert.ok(x>=0&&y>=0&&x+w<=width&&y+h<=height);
const feather=config.local_edit.feather_px;
assert.ok(Number.isInteger(feather)&&feather>=0&&feather<=6);
const mask=feather ? `<defs><linearGradient id="edge-x"><stop offset="0" stop-color="black"/><stop offset="${feather/w}" stop-color="white"/><stop offset="${1-feather/w}" stop-color="white"/><stop offset="1" stop-color="black"/></linearGradient><linearGradient id="edge-y" x2="0" y2="1"><stop offset="0" stop-color="black"/><stop offset="${feather/h}" stop-color="white"/><stop offset="${1-feather/h}" stop-color="white"/><stop offset="1" stop-color="black"/></linearGradient><mask id="mask-y" maskUnits="userSpaceOnUse" x="${x}" y="${y}" width="${w}" height="${h}"><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#edge-y)"/></mask><mask id="local-edge" maskUnits="userSpaceOnUse" x="${x}" y="${y}" width="${w}" height="${h}"><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#edge-x)" mask="url(#mask-y)"/></mask></defs>` : '';
const scene=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>北魏洛阳全景：永宁寺塔与原有空间环境修订 V16</title><desc>原V12全景作为底层，仅在指定寺院矩形内采用图像生成工具编辑的九层塔场景。图像不是考古相机标定或全城米制测绘，147米仍为候选，结构可行性尚未确立。</desc>${mask}<image data-kind="original-v12-background" href="./${config.background.file}" x="0" y="0" width="${width}" height="${height}" preserveAspectRatio="none"/><image data-kind="imagegen-local-scene" href="./${config.local_edit.file}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="none"${feather?' mask="url(#local-edge)"':''}/></svg>\n`;
await fs.writeFile(path.join(folder,'homepage-scene.svg'),scene);
// The source SVG stays editable and external-image based. Embed normalized PNG
// data only for portable librsvg rendering; no shape or vector pagoda is added.
const backgroundPNG=await sharp(background).png().toBuffer();
const render=scene.replace(`href="./${config.background.file}"`,`href="data:image/png;base64,${backgroundPNG.toString('base64')}"`)
  .replace(`href="./${config.local_edit.file}"`,`href="data:image/png;base64,${patch.toString('base64')}"`);
const png=await sharp(Buffer.from(render)).png().toBuffer();
await fs.writeFile(path.join(folder,'source-scene.png'),png);
const original=await sharp(background).removeAlpha().raw().toBuffer();
const final=await sharp(png).removeAlpha().raw().toBuffer();
assert.equal(original.length,final.length);
let outsideChanged=0,insideChanged=0,outsideMaxDelta=0;
for(let py=0;py<height;py++)for(let px=0;px<width;px++){
  const offset=(py*width+px)*3;
  const delta=Math.max(...[0,1,2].map(channel=>Math.abs(original[offset+channel]-final[offset+channel])));
  if(px>=x&&px<x+w&&py>=y&&py<y+h){if(delta)insideChanged++;}
  else{if(delta)outsideChanged++;outsideMaxDelta=Math.max(outsideMaxDelta,delta);}
}
assert.equal(outsideChanged,0,'The PNG must preserve decoded V12 RGB pixels outside the edit rectangle');
const fullPath=path.join(repo,'web/assets/luoyang-panorama-yongning-v16.webp');
const smallPath=path.join(repo,'web/assets/luoyang-panorama-yongning-v16-small.webp');
await sharp(png).webp({quality:92,effort:6}).toFile(fullPath);
await sharp(png).resize(960,540,{fit:'fill',kernel:'lanczos3'}).webp({quality:92,effort:6}).toFile(smallPath);
const audit={schema:'homepage-yongning-v16-render-audit-v1',source_kind:config.source_kind,canvas:config.canvas,
  local_rectangle_px:config.local_edit.rectangle_px,edge_feather_px:feather,
  background_sha256:sha(background),patch_sha256:sha(patch),svg_sha256:sha(Buffer.from(scene)),png_sha256:sha(png),
  full_webp_sha256:sha(await fs.readFile(fullPath)),small_webp_sha256:sha(await fs.readFile(smallPath)),
  outside_rectangle_pixels:width*height-w*h,outside_rectangle_changed_rgb_pixels:outsideChanged,
  outside_rectangle_max_channel_delta:outsideMaxDelta,inside_rectangle_changed_rgb_pixels:insideChanged,
  pixel_identity_applies_to:'source-scene.png decoded RGB only; not lossy WebP',
  new_vector_tower_geometry:false,rendering_dependencies:sharp.versions};
await fs.writeFile(path.join(folder,'render-audit.json'),JSON.stringify(audit,null,2)+'\n');
process.stdout.write(JSON.stringify(audit)+'\n');
