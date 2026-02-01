// 环境绑定类型
export type Bindings = {
  DB: D1Database;
};

// 币种信息
export interface Coin {
  id: number;
  symbol: string;
  name: string | null;
  rank_order: number;
  created_at: string;
}

// 价格记录
export interface PriceRecord {
  id: number;
  symbol: string;
  price: number;
  change_1h: number | null;
  change_24h: number | null;
  change_7d: number | null;
  market_cap: number | null;
  volume_24h: number | null;
  timestamp: string;
}

// 极值价格
export interface PriceExtreme {
  id: number;
  symbol: string;
  all_time_high: number;
  all_time_low: number;
  ath_date: string | null;
  atl_date: string | null;
  last_updated: string;
}

// 轮次统计
export interface RoundStat {
  id: number;
  round_time: string;
  green_count: number;
  red_count: number;
  green_ratio: number;
  extreme_up_count: number;
  extreme_down_count: number;
  surge_count: number;
  crash_count: number;
  risk_alert_count: number;
  created_at: string;
}

// 单币轮次详情
export interface CoinRoundDetail {
  id: number;
  symbol: string;
  round_time: string;
  price: number;
  prev_price: number | null;
  change_amount: number | null;
  change_percent: number | null;
  is_green: number;
  is_extreme_up: number;
  is_extreme_down: number;
  is_surge: number;
  is_crash: number;
  rank_in_round: number | null;
  created_at: string;
}

// 日统计
export interface DailyStat {
  id: number;
  date: string;
  symbol: string;
  total_surges: number;
  total_crashes: number;
  new_high_count: number;
  new_low_count: number;
  market_trend: string | null;
  trend_strength: number | null;
  star_rating: number;
  star_type: string | null;
  created_at: string;
}

// 极值记录
export interface ExtremeRecord {
  id: number;
  symbol: string;
  record_type: string;
  price: number;
  prev_extreme: number | null;
  zero_count: number;
  timestamp: string;
}

// 币种优先级
export interface CoinPriority {
  id: number;
  symbol: string;
  level: number;
  low_ratio: number;
  high_ratio: number;
  last_updated: string;
}

// CoinGecko API 响应类型
export interface CoinGeckoSimplePrice {
  [key: string]: {
    usd: number;
    usd_24h_change: number;
    usd_market_cap: number;
    usd_24h_vol: number;
  };
}

// 市场趋势类型
export type MarketTrend = 
  | '单边主升' 
  | '震荡偏多' 
  | '无序震荡' 
  | '震荡偏空' 
  | '单边主跌';

// 星级类型
export type StarType = '急涨' | '急跌';

// 币种等级
export type CoinLevel = 1 | 2 | 3 | 4 | 5 | 6;
