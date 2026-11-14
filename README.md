# PriVis 🔒📊

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

**PriVis** is an advanced framework and prototype system designed to assist data custodians in publishing privacy-preserving data visualizations. By incorporating user-defined **pattern constraints** and leveraging differentially private Bayesian networks, PriVis balances the critical trade-off between data privacy and analytical utility.

---

## 🌟 Key Features

* **Pattern Constraint Elicitation:** Allows data custodians to specify domain-specific patterns of interest by selecting visual elements and weighting their significance.
* **Weighted Bayesian Network Construction:** Replaces standard mutual information metrics with weighted mutual information to ensure crucial data correlations and patterns are preserved during synthesis.
* **Differential Privacy Integration:** Injects calibrated noise (such as Laplace noise) into joint probability distributions to satisfy rigorous privacy guarantees ($\epsilon$-differential privacy).
* **Iterative Evaluation Workflow:** Provides interactive views to inspect trade-offs between privacy budgets, data utility metrics, and visualization accuracy.

---

## 🛠️ Repository Architecture

```text
PriVis/
│
├── data/               # Sample datasets and input configurations
├── models/             # Core PriVis algorithms & Bayesian network logic
│   ├── bayesian.py     # Weighted Bayesian network generation
│   ├── constraints.py  # Pattern constraint parsing & mixture weights
│   └── privacy.py      # Noise injection mechanisms (Laplace/Exponential)
├── utils/              # Helper functions, metric calculations, and I/O
├── viz/                # Visualization rendering modules (DPVisCreator components)
├── main.py             # Main execution entry point
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
