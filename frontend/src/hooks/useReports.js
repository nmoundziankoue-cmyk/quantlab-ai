import { useMutation, useQuery } from "@tanstack/react-query";
import * as api from "../api/reportsApi";

export const useReportSections = () =>
  useQuery({ queryKey: ["report-sections"], queryFn: api.listReportSections, staleTime: Infinity });

export const useGenerateReport = () =>
  useMutation({ mutationFn: api.generateReport });

export const useGenerateSection = () =>
  useMutation({ mutationFn: api.generateSection });

export const useExportReportHtml = () =>
  useMutation({ mutationFn: api.exportReportHtml });
