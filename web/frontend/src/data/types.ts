export interface PiHistoryRound {
  round: number
  coverage: number
  totalCells: number
  meanFitness: number
  seedAsr: number
  seedDetection: number
  mutationAsr: number
  mutationDetection: number
  meanRisk: number
}

export interface PiElite {
  surface: string
  technique: string
  objective: string
  fitness: number
  text: string
  targetSpec?: Record<string, string>
}

export interface PromptInjectionData {
  archiveSize: number
  totalCells: number
  techniqueCounts: Record<string, number>
  objectiveCounts: Record<string, number>
  surfaceCounts: Record<string, number>
  history: PiHistoryRound[]
  sampleElites: PiElite[]
  allElites: PiElite[]
}

export interface TrSubclass {
  label: string
  n: number
  layer1: number | null
  layer2: number | null
  combined: number
  step: string
}

export interface TrDifficultyTier {
  label: string
  n: number
  share: number
  combinedRecall: number
}

export interface TrFeedbackEntry {
  tag: string
  title: string
  body: string
  before: string | null
  after: string | null
}

export interface TokenReplayData {
  testSetSize: number
  fraudCount: number
  legitimateCount: number
  precision: number
  recall: number
  f1: number
  auc: number | null
  confusion: { tn: number; fp: number; fn: number; tp: number }
  subclasses: TrSubclass[]
  difficultyTiers: TrDifficultyTier[]
  feedbackLoop: TrFeedbackEntry[]
  lastRun?: string
}

export interface MfEvadedSample {
  ownerAge: number
  businessCreditScore: number
  addressTenureMonths: number
  txnCount90d: number
  avgTxnAmount: number
  refundRatio: number
  fraudProbability: number
}

export interface MfTrainRow {
  model: string
  precision: number
  recall: number
  f1: number
  rocAuc: number
  prAuc: number
}

export interface MerchantFraudData {
  generated: number
  validTested: number
  detected: number
  evaded: number
  detectionRate: number
  evasionRate: number
  meanFraudProb: number
  threshold: number
  evadedSamples: MfEvadedSample[]
  trainCurve: MfTrainRow[]
  lastRun?: string
}

export interface GfEpoch {
  epoch: number
  topology: string
  amount_mean: number
  dwell_range: string
  node_f1_test: number
  node_precision_test: number
  node_recall_test: number
  node_auc_test: number
  node_pr_auc_test: number
  node_fpr_test: number
  node_threshold: number
  edge_f1_test: number
  edge_precision_test: number
  edge_recall_test: number
  edge_auc_test: number
  edge_pr_auc_test: number
  edge_fpr_test: number
  edge_threshold: number
  node_asr: number
  edge_asr: number
  combined_f1: number
  combined_auc: number
}

export interface GraphFraudData {
  epochs: GfEpoch[]
  nodeParams: number
  evolutionReports: string[]
  lastRun?: string
}

export interface ResultsData {
  promptInjection: PromptInjectionData
  tokenReplay: TokenReplayData
  merchantFraud: MerchantFraudData
  graphFraud: GraphFraudData
}
