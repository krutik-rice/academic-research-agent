export interface Paper {
  paper_id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  source: string;
  pdf_url: string | null;
  citation_count: number;
  keywords: string[];
}

export interface PaperContent {
  paper_id: string;
  text: string;
  sections: Record<string, string>;
  method: string;
}

export interface PaperSummary {
  paper_id: string;
  title: string;
  summary: string;
  limitations: string[];
  future_directions: string[];
  key_findings: string[];
  methodology: string;
  contributions: string[];
  keywords: string[];
}

export interface PaperAnalysis {
  paper_id: string;
  limitations: string[];
  future_directions: string[];
  method: string;
}

export interface AnalysisStatus {
  paper_id: string;
  title: string;
  analyzed: boolean;
  lim_count: number;
  fut_count: number;
}

export interface ResearchGapTheme {
  theme: string;
  papers: string[];
  frequency: number;
}

export interface ResearchGapsResult {
  themes: ResearchGapTheme[];
  analyzed_count: number;
  skipped_count: number;
}

export interface AgentStep {
  iteration: number;
  thought: string;
  action: string;
  action_input: string;
  observation: string;
  elapsed_s: number;
}

export interface AgentReport {
  paper_id: string;
  title: string;
  model: string;
  total_iterations: number;
  verdict: "worth_pursuing" | "partially_covered" | "well_covered" | "unclear";
  confidence: number;
  reasoning: string;
  gaps: string[];
  directions: string[];
  competing_work: string[];
  sources: string[];
  steps: AgentStep[];
}

export interface SummaryEntry {
  paper: Paper;
  summary: PaperSummary | null;
}

export interface GraphData {
  html: string;
  node_count: number;
  edge_count: number;
}

export type SseEvent<T = unknown> =
  | { type: "progress"; message: string; current?: number; total?: number }
  | { type: "done"; result?: T; report?: AgentReport; message?: string }
  | { type: "error"; message: string };
