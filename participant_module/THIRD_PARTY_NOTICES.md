# Third-party notices

No third-party source code is copied into this package. All code in `participant_module/` is the
team's own work under the MIT licence (see `LICENSE`).

At run time the module uses only packages of the common base environment and two models of the
organizer's model catalogue, read from the read-only model store:

| Component | Version / revision | Licence | Use |
|---|---|---|---|
| pypdfium2 | base environment | Apache-2.0 / BSD-3-Clause | PDF text extraction |
| torch | base environment | BSD-3-Clause | model inference on the CPU |
| transformers | base environment | Apache-2.0 | loading the NLI judge |
| sentence-transformers | base environment | Apache-2.0 | loading the reranker |
| cross-encoder/ms-marco-MiniLM-L6-v2 (catalog_id `ms-marco-minilm-l6-v2`) | 233902d25c440f23af6f7d6e94d2946bac0bee0a | Apache-2.0 | reranking retrieved passages |
| MoritzLaurer/deberta-v3-base-zeroshot-v2.0-c (catalog_id `deberta-v3-base-zeroshot-v2.0-c`) | bddf8c5411c34ac3565e16e04384fd68b2618dda | MIT | choosing the quoted evidence sentence |
