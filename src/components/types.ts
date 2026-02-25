export interface Statistic {
  [key: string]: string | number;
  label: string;
  value: number;
}

export interface ResearchAnswer {
  summary: string;
  details: string[];
  statistics: Statistic[];
  chart_type: "pie" | "bar" | "line";
  sources: string[];
}

export interface ParsedAnswer {
  summary: string;
  details: string[];
  statistics: Statistic[];
  chart_type: "bar" | "line" | "pie";
  sources: string[];
}

export interface ApiResponse {
  message: string;
  answer: ParsedAnswer;
  sources: string[];
  download_id: string;
}



// Utility to parse fenced JSON strings
export function extractJsonFromFencedString(raw: string): ResearchAnswer | null {
  const match = raw.match(/```json([\s\S]*?)```/);
  const jsonString = match ? match[1].trim() : raw.trim();

  try {
    return JSON.parse(jsonString) as ResearchAnswer;
  } catch (e) {
    console.error("Failed to parse JSON:", e);
    return null;
  }
}
