import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Crown, ArrowLeft, RefreshCw, Bot, Users } from 'lucide-react';
import apiClient from '../api/axios';

interface LeaderboardEntry {
  id: number;
  username: string;
  elo_rating: number;
  bot_elo?: number;
}

type LeaderboardTab = 'human' | 'bot';

const MEDALS = ['🥇', '🥈', '🥉'];
const RANK_COLORS = ['text-yellow-400', 'text-zinc-300', 'text-amber-600'];

const Leaderboard: React.FC = () => {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<LeaderboardTab>('human');

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true);
    try {
      const params = tab === 'bot' ? '?type=bot&limit=20' : '?limit=20';
      const res = await apiClient.get(`/api/users/leaderboard${params}`);
      setEntries(res.data);
      setError('');
    } catch {
      setError('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    fetchLeaderboard();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchLeaderboard, 30_000);

    // Refresh on focus
    const onFocus = () => fetchLeaderboard();
    window.addEventListener('focus', onFocus);

    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', onFocus);
    };
  }, [fetchLeaderboard]);

  const getElo = (e: LeaderboardEntry) => tab === 'bot' ? (e.bot_elo ?? 1200) : e.elo_rating;
  const maxElo = entries.length > 0 ? getElo(entries[0]) : 1200;
  const minElo = entries.length > 0 ? Math.min(...entries.map(getElo)) : 1200;
  const eloRange = Math.max(maxElo - minElo, 1);

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      {/* Nav */}
      <nav className="w-full px-6 py-4 flex items-center justify-between border-b border-zinc-800/50">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm"
        >
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex items-center gap-2">
          <span className="text-2xl">♟️</span>
          <span className="text-xl font-bold text-white">Pawnly</span>
        </div>
        <button
          onClick={fetchLeaderboard}
          className="text-zinc-400 hover:text-white transition-colors"
          title="Refresh"
        >
          <RefreshCw size={16} />
        </button>
      </nav>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center px-4 py-8 sm:py-12">
        {/* Title */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 mb-4">
            <Crown size={32} className="text-yellow-400" />
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Leaderboard
            </h1>
          </div>
          <p className="text-zinc-500 text-sm">Top players by Elo rating</p>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 mb-6 bg-zinc-900/80 rounded-xl p-1 border border-zinc-800/50">
          <button
            onClick={() => setTab('human')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all ${
              tab === 'human'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Users size={16} /> Human
          </button>
          <button
            onClick={() => setTab('bot')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all ${
              tab === 'bot'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Bot size={16} /> Bot
          </button>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <span className="inline-block w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-zinc-400">Loading leaderboard…</p>
          </div>
        ) : error ? (
          <div className="card max-w-sm w-full text-center">
            <p className="text-red-400 mb-4">{error}</p>
            <button onClick={fetchLeaderboard} className="btn-primary">
              Retry
            </button>
          </div>
        ) : entries.length === 0 ? (
          <div className="card max-w-sm w-full text-center">
            <p className="text-zinc-500">No players yet. Be the first!</p>
          </div>
        ) : (
          <div className="w-full max-w-xl space-y-2">
            {entries.map((entry, index) => {
              const rank = index + 1;
              const isTop3 = rank <= 3;
              const displayName = entry.username.includes('@')
                ? entry.username.split('@')[0]
                : entry.username;
              const displayElo = getElo(entry);
              const barWidth = ((displayElo - minElo) / eloRange) * 100;

              return (
                <div
                  key={entry.id}
                  className={`relative overflow-hidden rounded-xl border transition-all ${
                    isTop3
                      ? 'bg-zinc-800/80 border-zinc-700/80 py-4 px-5'
                      : 'bg-zinc-900/60 border-zinc-800/50 py-3 px-5'
                  }`}
                >
                  {/* Rating bar background */}
                  <div
                    className={`absolute inset-y-0 left-0 ${
                      isTop3 ? 'bg-emerald-500/10' : 'bg-zinc-700/20'
                    }`}
                    style={{ width: `${Math.max(barWidth, 5)}%` }}
                  />

                  <div className="relative flex items-center gap-4">
                    {/* Rank */}
                    <div className={`flex-shrink-0 w-10 text-center ${
                      isTop3 ? 'text-2xl' : 'text-zinc-500 font-mono text-sm'
                    }`}>
                      {isTop3 ? (
                        <span>{MEDALS[index]}</span>
                      ) : (
                        <span>#{rank}</span>
                      )}
                    </div>

                    {/* Name */}
                    <div className="flex-1 min-w-0">
                      <span className={`font-semibold truncate block ${
                        isTop3 ? 'text-white text-lg' : 'text-zinc-300'
                      }`}>
                        {displayName}
                      </span>
                    </div>

                    {/* Elo */}
                    <div className={`flex-shrink-0 font-bold font-mono tabular-nums ${
                      isTop3
                        ? `text-lg ${RANK_COLORS[index]}`
                        : 'text-zinc-400'
                    }`}>
                      {displayElo}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <footer className="text-center text-zinc-700 text-xs py-6 border-t border-zinc-800/30">
        Built with ♟️ — Pawnly
      </footer>
    </div>
  );
};

export default Leaderboard;
