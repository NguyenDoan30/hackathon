const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const workspace = path.resolve(__dirname, '..');
const runtime = workspace;
const runtimeRequire = createRequire(path.join(runtime, 'package.json'));
const ts = runtimeRequire('typescript');
const output = path.join(workspace, 'demo');
const modules = [];
const ids = new Map();
const styles = new Set();

function resolve(spec, parent) {
  if (spec === 'next/navigation') return path.join(__dirname, 'navigation-preview.ts');
  if (spec.startsWith('.') || path.isAbsolute(spec)) {
    const target = path.resolve(path.dirname(parent), spec);
    for (const suffix of ['', '.tsx', '.ts', '.js', '/index.tsx', '/index.ts', '/index.js']) {
      const candidate = target + suffix;
      if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
    }
    throw new Error('Cannot resolve ' + spec + ' from ' + parent);
  }
  return runtimeRequire.resolve(spec);
}

function add(file) {
  file = path.resolve(file);
  if (ids.has(file)) return ids.get(file);
  const id = modules.length;
  ids.set(file, id);
  modules.push('');
  if (file.endsWith('.css')) {
    styles.add(file);
    modules[id] = 'module.exports = {};';
    return id;
  }
  let source = fs.readFileSync(file, 'utf8');
  if (/\.tsx?$/.test(file)) {
    const result = ts.transpileModule(source, {
      fileName: file,
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
      reportDiagnostics: true,
    });
    const errors = (result.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error);
    if (errors.length) throw new Error(ts.formatDiagnosticsWithColorAndContext(errors, { getCurrentDirectory: () => workspace, getCanonicalFileName: f => f, getNewLine: () => '\n' }));
    source = result.outputText;
  }
  source = source.replace(/require\((['"])([^'"]+)\1\)/g, (_, quote, spec) => 'require(' + add(resolve(spec, file)) + ')');
  modules[id] = source;
  return id;
}

const entry = add(path.join(__dirname, 'preview-entry.tsx'));
fs.mkdirSync(output, { recursive: true });
const bundle = '(function(){"use strict";const process={env:{NODE_ENV:"production"}};const modules={\n' + modules.map((body,id) => id + ':function(require,module,exports){\n' + body + '\n}').join(',\n') + '\n};const cache={};function require(id){if(cache[id])return cache[id].exports;const module={exports:{}};cache[id]=module;modules[id](require,module,module.exports);return module.exports;}require(' + entry + ');})();';
const css = [...styles].map(file => fs.readFileSync(file, 'utf8')).join('\n');
fs.writeFileSync(path.join(output, 'app.js'), bundle);
fs.writeFileSync(path.join(output, 'app.css'), css);
const assetVersion = require('node:crypto').createHash('sha256').update(bundle + css).digest('hex').slice(0, 12);
fs.writeFileSync(path.join(output, 'index.html'), '<!doctype html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Luma · AI Study Assistant</title><meta name="description" content="Demo frontend AI Study Assistant"><link rel="stylesheet" href="./app.css?v=' + assetVersion + '"></head><body><div id="root"></div><script src="./app.js?v=' + assetVersion + '"></script></body></html>');
console.log('Built preview:', modules.length, 'modules;', Math.round(bundle.length/1024), 'KB JS;', Math.round(css.length/1024), 'KB CSS.');
