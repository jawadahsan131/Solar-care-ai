export type ApplianceType =
  | "ac"
  | "ceiling_fan"
  | "pedestal_fan"
  | "exhaust_fan"
  | "air_cooler"
  | "refrigerator"
  | "deep_freezer"
  | "microwave"
  | "electric_oven"
  | "water_dispenser"
  | "electric_kettle"
  | "washing_machine"
  | "iron"
  | "geyser"
  | "water_pump"
  | "tv"
  | "desktop_pc"
  | "laptop"
  | "router"
  | "ups"
  | "led_bulb"
  | "tube_light"
  | "phone_charger"
  | "vacuum_cleaner"
  | "other";

export type SourceTag = "label" | "catalog" | "guess" | "user";

export interface Appliance {
  id: string;
  home_id: string;
  room: string | null;
  type: ApplianceType;
  brand: string | null;
  model: string | null;
  capacity_value: number | null;
  capacity_unit: string | null;
  inverter: boolean | null;
  watts: number;
  duty_factor: number;
  surge_factor: number;
  qty: number;
  hourly_use: number[];
  is_essential: boolean;
  source_tag: SourceTag;
  confidence: number | null;
  user_verified: boolean;
  hours_per_day: number;
}

export interface Home {
  id: string;
  name: string;
  city: string | null;
  lat?: number | null;
  lon?: number | null;
  system_kw?: number | null;
  family_size: number | null;
  appliance_count?: number;
}

export interface DetectedItem {
  type: ApplianceType;
  brand?: string | null;
  model?: string | null;
  capacity_value?: number | null;
  capacity_unit?: string | null;
  inverter?: boolean | null;
  count: number;
  watts?: number | null;
  duty_factor: number;
  surge_factor: number;
  default_hours: number;
  confidence: number;
  source_tag: SourceTag;
  label_text?: string | null;
  bbox?: number[] | null;
  notes?: string | null;
}

export interface SizingOption {
  kind: "off_grid" | "hybrid" | "on_grid";
  panel_kw: number;
  inverter_kw: number;
  battery_kwh: number;
  notes: string[];
}

export interface SizingResult {
  daily_kwh: number;
  day_kwh: number;
  night_kwh: number;
  connected_kw: number;
  peak_kw: number;
  load_profile_kw: number[];
  running_profile_kw: number[];
  options: SizingOption[];
  breakdown: Array<{ type: ApplianceType; kwh: number; share: number }>;
  assumptions: Record<string, number>;
  warnings: string[];
}
