export async function GET(request) {
  return Response.json({
    predictions: [
      {
        id: 'pred_001',
        oracle: 'weather',
        event: 'NYC Temperature > 75F on Apr 10',
        probability: 0.72,
        confidence: 8,
        action: 'BUY_YES',
        reasoning: 'NWS forecast shows high-pressure system. Historical accuracy 85%.'
      },
      {
        id: 'pred_002',
        oracle: 'arbitrage',
        event: 'Kalshi-Polymarket price gap > 5%',
        probability: 0.68,
        confidence: 7,
        action: 'EXPLOIT_ARB',
        reasoning: 'Cross-platform analysis detects YES overpriced on Kalshi.'
      },
      {
        id: 'pred_003',
        oracle: 'whale',
        event: 'Institutional order imbalance',
        probability: 0.81,
        confidence: 9,
        action: 'FOLLOW_WHALE',
        reasoning: '$250K order cluster on YES side. Insider signal 9/10.'
      },
      {
        id: 'pred_004',
        oracle: 'politics',
        event: 'Policy announcement probability',
        probability: 0.55,
        confidence: 6,
        action: 'WAIT',
        reasoning: 'Multi-LLM consensus shows conflicting signals.'
      },
      {
        id: 'pred_005',
        oracle: 'sports',
        event: 'Team A victory probability',
        probability: 0.64,
        confidence: 7,
        action: 'BUY_YES',
        reasoning: 'Undervaluing home field. Edge 16.3%.'
      },
      {
        id: 'pred_006',
        oracle: 'equity',
        event: 'Stock > $150 by EOY',
        probability: 0.73,
        confidence: 7,
        action: 'BUY_YES',
        reasoning: 'Technical + insider patterns suggest 73%.'
      }
    ]
  });
}
