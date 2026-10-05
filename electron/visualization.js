/**
 * Renderer for the visualization window.
 *
 * Plot data arrives over the preload bridge rather than being interpolated
 * into the page source. The previous version built the page with
 * `const plotData = ${JSON.stringify(plotData)};` inside a <script> body, so
 * any `</script>` or U+2028 in the analysis data — a gene name, a sample
 * label, a free-text annotation — terminated the script element early and
 * the remainder was parsed as HTML.
 */

/* global Plotly */

(async function render() {
  const plotNode = document.getElementById('plot');
  const errorNode = document.getElementById('error');

  /** Show a failure instead of an empty window. */
  function fail(message) {
    plotNode.style.display = 'none';
    errorNode.style.display = 'block';
    errorNode.textContent = message;
  }

  if (typeof Plotly === 'undefined') {
    fail(
      'The bundled plotting library did not load. Reinstall dependencies ' +
      'with `npm install` so node_modules/plotly.js-dist-min is present.'
    );
    return;
  }

  if (!window.gliaent || typeof window.gliaent.invoke !== 'function') {
    fail('The preload bridge is unavailable, so plot data cannot be fetched.');
    return;
  }

  let response;
  try {
    response = await window.gliaent.invoke('viz:get-data');
  } catch (error) {
    fail(`Could not fetch plot data: ${error.message}`);
    return;
  }

  if (!response || !response.success) {
    fail(`Could not fetch plot data: ${(response && response.error) || 'unknown error'}`);
    return;
  }

  const payload = response.data || {};
  try {
    await Plotly.newPlot(
      plotNode,
      payload.data || [],
      payload.layout || {},
      { responsive: true, displaylogo: false }
    );
  } catch (error) {
    fail(`The plot could not be rendered: ${error.message}`);
  }
})();
