import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import type { Statistic, ResearchAnswer } from "./types";

// interface ChartProps {
//   data: Statistic[];
//   chartType: ResearchAnswer["chart_type"];
//   // title?: string;
// }

export const renderChart = (
  data: Statistic[],
  chartType: ResearchAnswer["chart_type"]
) => {
  switch (chartType) {
    case "line":
      return (
        <LineChart width={400} height={250} data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="value" stroke="#6366f1" />
        </LineChart>
      );

    case "pie":
      return (
        <PieChart width={400} height={250}>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            outerRadius={100}
            fill="#6366f1"
            label
          />
          <Tooltip />
          <Legend />
        </PieChart>
      );

    default: // "bar"
      return (
        <BarChart width={400} height={250} data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill="#6366f1" />
        </BarChart>
      );
  }
};
