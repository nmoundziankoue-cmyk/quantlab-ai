import { useQuery } from "@tanstack/react-query";
import * as api from "../api/newsIntelligenceApi";

export const useNewsFeed = (params) =>
  useQuery({ queryKey: ["news-feed", params], queryFn: () => api.getNewsFeed(params), refetchInterval: 30000 });

export const useBreakingNews = (params) =>
  useQuery({ queryKey: ["breaking-news", params], queryFn: () => api.getBreakingNews(params), refetchInterval: 15000 });

export const useTickerNews = (ticker, params) =>
  useQuery({ queryKey: ["ticker-news", ticker, params], queryFn: () => api.getTickerNews(ticker, params), enabled: !!ticker });

export const useSectorNews = (sector, params) =>
  useQuery({ queryKey: ["sector-news", sector, params], queryFn: () => api.getSectorNews(sector, params), enabled: !!sector });

export const useDailySummary = () =>
  useQuery({ queryKey: ["daily-summary"], queryFn: api.getDailySummary, refetchInterval: 300000 });

export const useNewsClusters = () =>
  useQuery({ queryKey: ["news-clusters"], queryFn: api.getNewsClusters });

export const useNewsImpact = (params) =>
  useQuery({ queryKey: ["news-impact", params], queryFn: () => api.getNewsImpact(params) });
