/**
 * RealDeal AI - Investment Heatmap
 *
 * Uses Leaflet + OpenStreetMap (100% free, no API key needed)
 * instead of Mapbox GL (paid).
 *
 * Features:
 * - Color-coded circle markers (green = high score, red = low)
 * - Click for property details popup
 * - Legend showing score ranges
 * - Layer controls for toggling overlays
 * - Dark theme styling via CartoDB dark tiles
 * - OpenStreetMap tile layer (free, no usage limits)
 */

import { useEffect, useMemo, useRef } from "react";
import {
  CircleMarker,
  LayerGroup,
  LayersControl,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import type { Map as LeafletMap } from "leaflet";
import "leaflet/dist/leaflet.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HeatmapPoint {
  lat: number;
  lng: number;
  score: number; // 0-100
  address?: string;
  price?: number;
  cashFlow?: number;
  capRate?: number;
  propertyId?: string;
}

interface HeatmapProps {
  points: HeatmapPoint[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  onMarkerClick?: (point: HeatmapPoint) => void;
}

// ---------------------------------------------------------------------------
// Score-to-color mapping
// ---------------------------------------------------------------------------

function scoreToColor(score: number): string {
  if (score >= 80) return "#16a34a"; // green-600 -- excellent
  if (score >= 65) return "#65a30d"; // lime-600 -- good
  if (score >= 50) return "#ca8a04"; // yellow-600 -- fair
  if (score >= 35) return "#ea580c"; // orange-600 -- below average
  return "#dc2626"; // red-600 -- poor
}

function scoreToLabel(score: number): string {
  if (score >= 80) return "Excellent";
  if (score >= 65) return "Good";
  if (score >= 50) return "Fair";
  if (score >= 35) return "Below Avg";
  return "Poor";
}

function scoreToRadius(score: number): number {
  // Larger radius for higher-scoring properties (more visible)
  return Math.max(6, Math.min(14, 6 + (score / 100) * 8));
}

// ---------------------------------------------------------------------------
// Auto-fit bounds when points change
// ---------------------------------------------------------------------------

function FitBounds({ points }: { points: HeatmapPoint[] }) {
  const map = useMap();

  useEffect(() => {
    if (points.length === 0) return;

    const lats = points.map((p) => p.lat);
    const lngs = points.map((p) => p.lng);
    const bounds: [[number, number], [number, number]] = [
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)],
    ];

    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }, [points, map]);

  return null;
}

// ---------------------------------------------------------------------------
// Legend component
// ---------------------------------------------------------------------------

function Legend() {
  const map = useMap();
  const legendRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (legendRef.current) return; // already mounted

    const L = (window as any).L;
    if (!L) return;

    const legend = L.control({ position: "bottomright" });

    legend.onAdd = () => {
      const div = L.DomUtil.create("div", "leaflet-control");
      div.style.cssText =
        "background: rgba(17,24,39,0.9); padding: 10px 14px; border-radius: 8px; " +
        "color: #e5e7eb; font-size: 12px; line-height: 1.8; backdrop-filter: blur(4px); " +
        "border: 1px solid rgba(255,255,255,0.1);";

      div.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 4px; font-size: 13px;">Investment Score</div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#16a34a;margin-right:6px;vertical-align:middle;"></span>80-100 Excellent</div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#65a30d;margin-right:6px;vertical-align:middle;"></span>65-79 Good</div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ca8a04;margin-right:6px;vertical-align:middle;"></span>50-64 Fair</div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ea580c;margin-right:6px;vertical-align:middle;"></span>35-49 Below Avg</div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#dc2626;margin-right:6px;vertical-align:middle;"></span>0-34 Poor</div>
      `;

      legendRef.current = div;
      return div;
    };

    legend.addTo(map);

    return () => {
      legend.remove();
      legendRef.current = null;
    };
  }, [map]);

  return null;
}

// ---------------------------------------------------------------------------
// Heatmap component
// ---------------------------------------------------------------------------

export default function Heatmap({
  points,
  center,
  zoom = 11,
  height = "500px",
  onMarkerClick,
}: HeatmapProps) {
  const defaultCenter: [number, number] = useMemo(() => {
    if (center) return center;
    if (points.length === 0) return [39.8283, -98.5795]; // center of US
    const avgLat = points.reduce((s, p) => s + p.lat, 0) / points.length;
    const avgLng = points.reduce((s, p) => s + p.lng, 0) / points.length;
    return [avgLat, avgLng];
  }, [center, points]);

  // Group points by score range for layer controls
  const grouped = useMemo(() => {
    const excellent: HeatmapPoint[] = [];
    const good: HeatmapPoint[] = [];
    const fair: HeatmapPoint[] = [];
    const belowAvg: HeatmapPoint[] = [];
    const poor: HeatmapPoint[] = [];

    for (const p of points) {
      if (p.score >= 80) excellent.push(p);
      else if (p.score >= 65) good.push(p);
      else if (p.score >= 50) fair.push(p);
      else if (p.score >= 35) belowAvg.push(p);
      else poor.push(p);
    }

    return { excellent, good, fair, belowAvg, poor };
  }, [points]);

  const formatPrice = (n?: number) =>
    n != null ? `$${n.toLocaleString()}` : "N/A";
  const formatCashFlow = (n?: number) =>
    n != null ? `$${n.toLocaleString()}/mo` : "N/A";
  const formatCapRate = (n?: number) =>
    n != null ? `${(n * 100).toFixed(1)}%` : "N/A";

  const renderMarkers = (pts: HeatmapPoint[]) =>
    pts.map((point, idx) => (
      <CircleMarker
        key={`${point.lat}-${point.lng}-${idx}`}
        center={[point.lat, point.lng]}
        radius={scoreToRadius(point.score)}
        pathOptions={{
          color: scoreToColor(point.score),
          fillColor: scoreToColor(point.score),
          fillOpacity: 0.7,
          weight: 2,
          opacity: 0.9,
        }}
        eventHandlers={{
          click: () => onMarkerClick?.(point),
        }}
      >
        <Popup>
          <div style={{ minWidth: 200, fontFamily: "system-ui, sans-serif" }}>
            <div
              style={{
                fontWeight: 700,
                fontSize: 14,
                marginBottom: 6,
                color: "#111827",
              }}
            >
              {point.address || "Property"}
            </div>
            <div
              style={{
                display: "inline-block",
                padding: "2px 8px",
                borderRadius: 4,
                backgroundColor: scoreToColor(point.score),
                color: "white",
                fontWeight: 600,
                fontSize: 12,
                marginBottom: 8,
              }}
            >
              Score: {point.score}/100 ({scoreToLabel(point.score)})
            </div>
            <table style={{ width: "100%", fontSize: 12, marginTop: 6 }}>
              <tbody>
                <tr>
                  <td style={{ color: "#6b7280", padding: "2px 0" }}>Price</td>
                  <td style={{ textAlign: "right", fontWeight: 600 }}>
                    {formatPrice(point.price)}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "#6b7280", padding: "2px 0" }}>
                    Cash Flow
                  </td>
                  <td
                    style={{
                      textAlign: "right",
                      fontWeight: 600,
                      color:
                        point.cashFlow != null && point.cashFlow > 0
                          ? "#16a34a"
                          : "#dc2626",
                    }}
                  >
                    {formatCashFlow(point.cashFlow)}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "#6b7280", padding: "2px 0" }}>
                    Cap Rate
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 600 }}>
                    {formatCapRate(point.capRate)}
                  </td>
                </tr>
              </tbody>
            </table>
            {point.propertyId && (
              <div style={{ marginTop: 8, textAlign: "center" }}>
                <a
                  href={`/properties/${point.propertyId}`}
                  style={{
                    color: "#1a56db",
                    fontWeight: 600,
                    fontSize: 12,
                    textDecoration: "none",
                  }}
                >
                  View Full Analysis
                </a>
              </div>
            )}
          </div>
        </Popup>
      </CircleMarker>
    ));

  return (
    <div style={{ height, width: "100%", borderRadius: 12, overflow: "hidden" }}>
      <MapContainer
        center={defaultCenter}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        zoomControl={true}
      >
        {/* Dark theme tile layer (CartoDB Dark Matter -- free) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Layer controls for toggling score groups */}
        <LayersControl position="topright">
          <LayersControl.Overlay checked name="Excellent (80-100)">
            <LayerGroup>{renderMarkers(grouped.excellent)}</LayerGroup>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Good (65-79)">
            <LayerGroup>{renderMarkers(grouped.good)}</LayerGroup>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Fair (50-64)">
            <LayerGroup>{renderMarkers(grouped.fair)}</LayerGroup>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Below Avg (35-49)">
            <LayerGroup>{renderMarkers(grouped.belowAvg)}</LayerGroup>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Poor (0-34)">
            <LayerGroup>{renderMarkers(grouped.poor)}</LayerGroup>
          </LayersControl.Overlay>

          {/* Optional: switch to standard OSM tiles */}
          <LayersControl.BaseLayer name="Standard">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer checked name="Dark">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {/* Auto-fit map to points */}
        <FitBounds points={points} />

        {/* Legend */}
        <Legend />
      </MapContainer>
    </div>
  );
}
