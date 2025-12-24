import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler)

export default function SparklineChart({ data, color }) {
  const chartData = {
    labels: data.map((_, i) => i),
    datasets: [{
      data,
      borderColor: color,
      backgroundColor: `${color}15`,
      borderWidth: 1.5,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
    }]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: { display: false, min: 0, max: 100 }
    },
    elements: { line: { borderCapStyle: 'round' } }
  }

  return (
    <div className="h-6 w-full">
      <Line data={chartData} options={options} />
    </div>
  )
}
