import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { economicCalendarApi } from "../api/economicCalendarApi";

export function useEconomicEvents(params = {}) {
  return useQuery({
    queryKey: ["economic-events", params],
    queryFn: () => economicCalendarApi.listEvents(params),
    staleTime: 120000,
    select: (data) => (Array.isArray(data) ? data : []),
  });
}

export function useUpcomingEvents(days = 7) {
  return useQuery({
    queryKey: ["upcoming-events", days],
    queryFn: () => economicCalendarApi.getUpcoming(days),
    staleTime: 300000,
    select: (data) => (Array.isArray(data) ? data : []),
  });
}

export function useHighImpactEvents() {
  return useQuery({
    queryKey: ["high-impact-events"],
    queryFn: () => economicCalendarApi.getHighImpact(),
    staleTime: 300000,
    select: (data) => (Array.isArray(data) ? data : []),
  });
}

export function useImpactSummary() {
  return useQuery({
    queryKey: ["impact-summary"],
    queryFn: economicCalendarApi.getImpactSummary,
    staleTime: 300000,
  });
}

export function useCreateEconomicEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: economicCalendarApi.createEvent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["economic-events"] }),
  });
}

export function useSeedEvents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: economicCalendarApi.seed,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["economic-events"] }),
  });
}
