import { useMemo } from 'react';
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import {
  allocationByStrategy,
  strategyAllocationLabel,
} from '../utils/allocation.js';

const COLORS = [
  '#66fcf1',
  '#45a29e',
  '#bd93f9',
  '#ffb86c',
  '#ff5555',
  '#50fa7b',
  '#f1fa8c',
];

export default function AllocationChart({ weighted }) {
  const data = useMemo(() => allocationByStrategy(weighted), [weighted]);

  return (
    <div className="glass-panel">
      <h3 className="section-heading">Allocation by Strategy</h3>
      <div className="allocation-chart" aria-label="Allocation by strategy chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={5}
              dataKey="value"
              label={strategyAllocationLabel}
              labelLine={{ stroke: '#8b929a', strokeWidth: 1 }}
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(0,0,0,0.8)',
                border: '1px solid var(--panel-border)',
                borderRadius: '8px',
              }}
              itemStyle={{ color: '#fff' }}
              formatter={(value) => [`${value}%`, 'Allocation']}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
