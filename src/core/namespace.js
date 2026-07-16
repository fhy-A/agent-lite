(function initializeCodeNamespace(global) {
  "use strict";

  const Code = global.Code || {};
  Code.core = Code.core || {};
  Code.services = Code.services || {};
  Code.features = Code.features || {};
  Code.agent = Code.agent || {};
  Code.ui = Code.ui || {};
  global.Code = Code;
})(window);
