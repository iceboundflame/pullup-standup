var webpack = require('webpack');

var config = {
  context: __dirname + "/app",
  entry: "./main.js",

  output: {
    filename: "bundle.js",
    path: __dirname + "/dist",
  },

  module: {
    loaders: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        query: {
          presets: ['react', 'es2015'],
        },
      },

      { test: /autobahn\/package.json$/,
        loader: 'json-loader' },
    ],
  },

  plugins: [
    new webpack.ContextReplacementPlugin(/bindings$/, /^$/)
  ],
};
module.exports = config;
