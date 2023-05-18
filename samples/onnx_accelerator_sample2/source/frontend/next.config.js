// Original Copyright Microsoft Corporation. Licensed under the MIT License.
// Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

/** @type {import('next').NextConfig} */
const NodePolyfillPlugin = require("node-polyfill-webpack-plugin");
const CopyPlugin = require("copy-webpack-plugin");

module.exports = {
    reactStrictMode: true,
    webpack: (config, {}) => {

        config.resolve.extensions.push(".ts", ".tsx");
        config.resolve.fallback = {fs: false};

        config.plugins.push(
            new NodePolyfillPlugin(),
            new CopyPlugin({
                patterns: [
                    {
                        from: './node_modules/onnxruntime-web/dist/ort-wasm.wasm',
                        to: 'static/chunks/pages',
                    },
                    {
                        from: './node_modules/onnxruntime-web/dist/ort-wasm-simd.wasm',
                        to: 'static/chunks/pages',
                    }
                ],
            }),
        );

        return config;
    }
}
