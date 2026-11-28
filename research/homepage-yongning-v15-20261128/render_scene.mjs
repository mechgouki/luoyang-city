/** Render the native SVG scene using the generated courtyard as a texture asset.
 * This assembles an editable SVG scene, not a bitmap retouching operation.
 * Usage: NODE_PATH or CODEX_PRIMARY_RUNTIME_NODE_MODULES must resolve sharp.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const sharp=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES
  ? path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'sharp') : 'sharp');
const folder=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(folder,'../..');
const tower=await fs.readFile(path.join(folder,'tower-layer.svg'),'utf8');
const background=await fs.readFile(path.join(folder,'courtyard-background.png'));
const open=tower.match(/^<svg[^>]*>/)[0];
const body=tower.slice(open.length).replace(/<\/svg>\s*$/,'');
const description='<title>北魏洛阳全景：永宁寺塔依V6参数修订</title><desc>艺术全景背景与V6九层塔原生投影层。画面投影并非历史相机配准，147米为候选方案，结构可行性尚未确立。</desc>';
const root='<svg xmlns="http://www.w3.org/2000/svg" width="1672" height="941" viewBox="0 0 1672 941">';
const scene=root+description+'<image href="./courtyard-background.png" x="0" y="0" width="1672" height="941"/>'+body+'</svg>\n';
await fs.writeFile(path.join(folder,'homepage-scene.svg'),scene);
// Embed the existing asset only for portable librsvg rendering; the checked-in
// scene retains its independently hashed external background and editable tower.
const render=scene.replace('href="./courtyard-background.png"','href="data:image/png;base64,'+background.toString('base64')+'"');
const png=await sharp(Buffer.from(render)).png().toBuffer();
await fs.writeFile(path.join(folder,'homepage-panorama-v15.png'),png);
await sharp(png).webp({quality:92,effort:6}).toFile(path.join(repo,'web/assets/luoyang-panorama-yongning-v15.webp'));
await sharp(png).resize(960,540,{fit:'fill',kernel:'lanczos3'}).webp({quality:92,effort:6}).toFile(path.join(repo,'web/assets/luoyang-panorama-yongning-v15-small.webp'));
process.stdout.write(JSON.stringify({scene:'homepage-scene.svg',render:'homepage-panorama-v15.png',size:[1672,941],mobile:[960,540]})+'\n');
