# Foreground detection

The converter uses the compact U²-Net model by Xuebin Qin and coauthors for salient object detection. The self-hosted ONNX weights are the u2netp export distributed by rembg (MD5 8e83ca70e441ab06c318d82300c84806). [Model project](https://github.com/xuebinqin/U-2-Net) · [ONNX distribution](https://github.com/danielgatis/rembg/releases/tag/v0.0.0) · [Model project license](U2NET-LICENSE)

The browser runs inference in a Web Worker using the single-threaded WebAssembly backend of ONNX Runtime Web 1.20.1. The runtime, model and image processing are hosted with the demo. [Runtime distribution](https://www.npmjs.com/package/onnxruntime-web/v/1.20.1) · [Runtime license](ORT-LICENSE) · [Third-party notices](ORT-NOTICES.txt)
