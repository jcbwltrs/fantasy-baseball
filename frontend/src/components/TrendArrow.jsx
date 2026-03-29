import { trendIndicator } from '../utils/scoring';

export default function TrendArrow({ trend }) {
  const { symbol, color } = trendIndicator(trend);
  return (
    <span className={`font-bold ${color}`} title={`${trend > 0 ? '+' : ''}${trend.toFixed(1)} vs season avg`}>
      {symbol} {Math.abs(trend).toFixed(1)}
    </span>
  );
}
