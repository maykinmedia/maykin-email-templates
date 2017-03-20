#!/usr/bin/env node

/**
 * Utility script to leverage jpsm/SystemJS' power to build the depcache
 * for a given package.
 *
 * This traces the module and extracts the relative paths to all the
 * files used.
 */

var fs = require('fs');
var inlineCss = require('inline-css');
var htmlmin = require('htmlmin');
var minify = require('html-minifier').minify;


var file_name = process.argv[2];  // 0 is node, 1 is the file
var html = fs.readFileSync(file_name, {encoding: 'utf-8'});
var inline_options = {
    applyStyleTags: false,
    removeStyleTags: true,
    preserveMediaQueries: true,
    removeLinkTags: false,
    applyWidthAttributes: true,
    applyTableAttributes: true,
    url: 'http://localhost:8000'
};

inlineCss(html, inline_options)
.then(function(html) {
    process.stdout.write(minify(html, {collapseWhitespace: true, minifyCSS: true}));
});
