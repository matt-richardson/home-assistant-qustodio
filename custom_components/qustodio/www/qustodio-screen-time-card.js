// Screen time card for the Qustodio integration. Filled in by the next commits.
class QustodioScreenTimeCard extends HTMLElement {
  setConfig(config) {
    this._config = config;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("qustodio-screen-time-card", QustodioScreenTimeCard);
