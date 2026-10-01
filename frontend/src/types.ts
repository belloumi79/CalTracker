export type Nutrients = {
  calories: number
  protein_g: number
  carbohydrates_g: number
  fat_g: number
  fiber_g: number
  sugar_g: number
  sodium_mg: number
}

export type Targets = {
  [K in keyof Nutrients]: number | null
} & {
  basis: string
  estimated: boolean
}

export type Profile = {
  id: string
  email: string
  display_name: string
  age: number | null
  sex: string | null
  height_cm: number | null
  weight_kg: number | null
  activity_level: string | null
  goals: string[]
  dietary_preferences: string[]
  allergies: string[]
  intolerances: string[]
  favorite_foods: string[]
  avoid_foods: string[]
  meals_per_day: number | null
  country: string | null
  food_budget: number | null
  cultural_constraints: string | null
  daily_calorie_target: number | null
  created_at: string
  updated_at: string
}

export type DailySummary = {
  date: string
  consumed: Nutrients
  targets: Targets
  deviations: Record<string, number | null>
  macro_distribution: Record<string, number>
  meal_count: number
  water_ml: number
  known_nutrition: boolean
  unknown_item_count: number
  trend: string
  disclaimer: string
}

export type MealItem = {
  id: string
  food_id: string | null
  food_name: string
  quantity: number
  unit: string
  nutrition: Partial<Nutrients> | null
  nutrition_known: boolean
  nutrition_source: string | null
  confidence: string
}

export type Meal = {
  id: string
  meal_type: string
  eaten_at: string
  description: string | null
  items: MealItem[]
  totals: Nutrients
  has_unknown_nutrition: boolean
  created_at: string
}

export type PeriodSummary = {
  start_date: string
  end_date: string
  days: Array<{
    date: string
    consumed: Nutrients
    meal_count: number
    water_ml: number
    known_nutrition: boolean
  }>
  totals: Nutrients
  averages: Nutrients
  average_meals: number
  goal_adherence: number | null
  disclaimer: string
}

export type ParsedItem = {
  food: string
  quantity: number | null
  unit: string | null
  estimated: boolean
  confidence: string
  needs_clarification: boolean
}

export type Suggestion = {
  title: string
  ingredients: Array<{
    food: string
    quantity: number | null
    unit: string | null
    estimated: boolean
    nutrition_known: boolean
  }>
  nutrition: Partial<Nutrients>
  estimated: boolean
  notes: string[]
}
