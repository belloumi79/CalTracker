import { CSSProperties, FormEvent, useEffect, useMemo, useState } from 'react'
import { api, ApiError, clearToken, getToken, saveToken } from './api'
import type { DailySummary, Meal, PeriodSummary, ParsedItem, Profile, Suggestion } from './types'
import './styles.css'

type View = 'dashboard' | 'log' | 'history' | 'coach' | 'profile' | 'privacy'

const nutrientLabels: Record<string, string> = {
  calories: 'Calories',
  protein_g: 'Protéines',
  carbohydrates_g: 'Glucides',
  fat_g: 'Lipides',
  fiber_g: 'Fibres',
  sugar_g: 'Sucres',
  sodium_mg: 'Sodium',
}

const formatNumber = (value: number | null | undefined, digits = 0) =>
  value === null || value === undefined ? '—' : new Intl.NumberFormat('fr-FR', { maximumFractionDigits: digits }).format(value)

const today = () => new Date().toISOString().slice(0, 10)

function App() {
  const [token, setToken] = useState(getToken())
  if (!token) return <AuthScreen onAuthenticated={(value) => { saveToken(value); setToken(value) }} />
  return <Workspace onLogout={() => { clearToken(); setToken(null) }} />
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('register')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      if (mode === 'register') {
        await api.register({ email, password, display_name: displayName })
      }
      const result = await api.login({ email, password })
      onAuthenticated(result.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de se connecter.')
    } finally { setBusy(false) }
  }

  return <main className="auth-shell">
    <section className="auth-panel">
      <div className="brand-lockup"><span className="brand-mark">✦</span><span>CalTracker</span></div>
      <div className="auth-copy">
        <p className="eyebrow">Votre boussole quotidienne</p>
        <h1>Comprendre vos habitudes, sans jugement.</h1>
        <p>Un journal nutritionnel privé qui rassemble vos repas, rend les tendances lisibles et vous laisse décider de la suite.</p>
      </div>
      <div className="auth-note"><span>⌁</span><p>Vos recommandations sont informatives. CalTracker ne remplace jamais un médecin ou un diététicien.</p></div>
    </section>
    <section className="auth-card">
      <div className="tab-list" role="tablist">
        <button className={mode === 'register' ? 'tab active' : 'tab'} onClick={() => setMode('register')}>Créer un compte</button>
        <button className={mode === 'login' ? 'tab active' : 'tab'} onClick={() => setMode('login')}>Se connecter</button>
      </div>
      <h2>{mode === 'register' ? 'Commencer simplement' : 'Ravi de vous revoir'}</h2>
      <p className="muted">{mode === 'register' ? 'Quelques informations, puis votre premier repas.' : 'Retrouvez votre journal personnel.'}</p>
      <form onSubmit={submit} className="stack-form">
        {mode === 'register' && <label>Nom d’affichage<input value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="Camille" required maxLength={80} /></label>}
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="vous@exemple.fr" required /></label>
        <label>Mot de passe<input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="8 caractères minimum" required minLength={mode === 'register' ? 8 : 1} /></label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary-button full" disabled={busy}>{busy ? 'Un instant…' : mode === 'register' ? 'Créer mon espace' : 'Ouvrir mon espace'}</button>
      </form>
      <p className="legal-copy">En continuant, vous acceptez que vos données servent uniquement à votre suivi et à vos demandes. <button className="link-button" onClick={() => setMode('login')}>En savoir plus</button></p>
    </section>
  </main>
}

function Workspace({ onLogout }: { onLogout: () => void }) {
  const [view, setView] = useState<View>('dashboard')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [daily, setDaily] = useState<DailySummary | null>(null)
  const [weekly, setWeekly] = useState<PeriodSummary | null>(null)
  const [meals, setMeals] = useState<Meal[]>([])
  const [recommendations, setRecommendations] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = async () => {
    setLoading(true); setError('')
    try {
      const [nextProfile, nextDaily, nextWeekly, nextMeals, nextRecommendations] = await Promise.all([
        api.profile(), api.daily(), api.weekly(), api.meals(), api.recommendations(),
      ])
      setProfile(nextProfile); setDaily(nextDaily); setWeekly(nextWeekly); setMeals(nextMeals); setRecommendations(nextRecommendations.recommendations)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) onLogout()
      else setError(err instanceof Error ? err.message : 'Les données ne sont pas disponibles.')
    } finally { setLoading(false) }
  }

  useEffect(() => { void refresh() }, [])

  const displayName = profile?.display_name?.split(' ')[0] || 'vous'
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand-lockup"><span className="brand-mark">✦</span><span>CalTracker</span></div>
      <div className="sidebar-profile"><div className="avatar">{displayName[0]?.toUpperCase()}</div><div><strong>{profile?.display_name || 'Votre espace'}</strong><span>Journal personnel</span></div></div>
      <nav className="main-nav" aria-label="Navigation principale">
        <NavButton icon="◷" label="Aujourd’hui" active={view === 'dashboard'} onClick={() => setView('dashboard')} />
        <NavButton icon="＋" label="Ajouter un repas" active={view === 'log'} onClick={() => setView('log')} />
        <NavButton icon="▤" label="Historique" active={view === 'history'} onClick={() => setView('history')} />
        <NavButton icon="✧" label="Coach IA" active={view === 'coach'} onClick={() => setView('coach')} />
      </nav>
      <div className="sidebar-bottom">
        <NavButton icon="⚙" label="Mon profil" active={view === 'profile'} onClick={() => setView('profile')} />
        <NavButton icon="⌁" label="Confidentialité" active={view === 'privacy'} onClick={() => setView('privacy')} />
        <button className="logout-button" onClick={onLogout}>↪ <span>Se déconnecter</span></button>
      </div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div className="mobile-brand"><span className="brand-mark">✦</span>CalTracker</div><div className="topbar-actions"><span className="sync-dot">●</span> Données privées <button className="avatar small" onClick={() => setView('profile')}>{displayName[0]?.toUpperCase()}</button></div></header>
      {error && <div className="alert error-banner">{error}<button onClick={() => setError('')}>×</button></div>}
      {loading ? <LoadingState /> : profile && daily && <>
        {view === 'dashboard' && <Dashboard profile={profile} daily={daily} weekly={weekly} meals={meals} recommendations={recommendations} onNavigate={setView} />}
        {view === 'log' && <LogMeal onSaved={refresh} />}
        {view === 'history' && <History meals={meals} weekly={weekly} onDelete={async id => { await api.removeMeal(id); await refresh() }} />}
        {view === 'coach' && <Coach recommendations={recommendations} onRefresh={refresh} />}
        {view === 'profile' && <ProfileEditor profile={profile} onSaved={refresh} />}
        {view === 'privacy' && <Privacy />}
      </>}
    </main>
  </div>
}

function NavButton({ icon, label, active, onClick }: { icon: string; label: string; active: boolean; onClick: () => void }) {
  return <button className={active ? 'nav-button active' : 'nav-button'} onClick={onClick}><span className="nav-icon">{icon}</span><span>{label}</span></button>
}

function LoadingState() { return <div className="loading-state"><div className="spinner" /><p>Préparation de votre espace…</p></div> }

function Dashboard({ profile, daily, weekly, meals, recommendations, onNavigate }: { profile: Profile; daily: DailySummary; weekly: PeriodSummary | null; meals: Meal[]; recommendations: string[]; onNavigate: (view: View) => void }) {
  const completion = daily.targets.calories ? Math.min(100, Math.round((daily.consumed.calories / daily.targets.calories) * 100)) : 0
  const greeting = new Date().getHours() < 18 ? 'Bonjour' : 'Bonsoir'
  return <div className="page dashboard-page">
    <div className="page-heading"><div><p className="eyebrow">{new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}</p><h1>{greeting}, {profile.display_name.split(' ')[0]} <span className="wave">✦</span></h1><p className="muted">Un petit aperçu de votre journée, à votre rythme.</p></div><button className="primary-button" onClick={() => onNavigate('log')}>＋ Ajouter un repas</button></div>
    <div className="dashboard-grid">
      <section className="card calorie-card"><div className="card-heading"><div><p className="card-kicker">Énergie du jour</p><h2>{formatNumber(daily.consumed.calories)} <small>kcal</small></h2></div><div className="ring" style={{ '--progress': `${completion}%` } as CSSProperties}><span>{daily.targets.calories ? `${completion}%` : '—'}</span></div></div><div className="progress-line"><span style={{ width: `${completion}%` }} /></div><div className="metric-foot"><span>Consommé</span><strong>{daily.targets.calories ? `${formatNumber(daily.targets.calories)} kcal cible` : 'Ajoutez votre profil pour une cible'}</strong></div></section>
      <section className="card mini-stat"><div className="icon-bubble green">⌁</div><p className="card-kicker">Repas enregistrés</p><h2>{daily.meal_count}<small> / jour</small></h2><p className="stat-caption">{daily.meal_count === 0 ? 'Votre premier repas vous attend' : 'Continuez comme ça'}</p></section>
      <section className="card mini-stat"><div className="icon-bubble peach">◌</div><p className="card-kicker">Hydratation</p><h2>{formatNumber(daily.water_ml / 1000, 1)}<small> L</small></h2><p className="stat-caption">Saisie optionnelle</p></section>
    </div>
    <div className="two-column">
      <section className="card"><div className="section-heading"><div><p className="card-kicker">Répartition</p><h2>Vos nutriments</h2></div><span className="subtle-pill">Données connues</span></div><NutrientBars daily={daily} /></section>
      <section className="card recommendation-card"><div className="section-heading"><div><p className="card-kicker">Votre fil du jour</p><h2>À retenir</h2></div><span className="sparkle">✧</span></div>{recommendations.slice(0, 3).map((recommendation, index) => <div className="recommendation" key={recommendation}><span className={`rec-number rec-${index}`}>{String(index + 1).padStart(2, '0')}</span><p>{recommendation}</p></div>)}<button className="text-button" onClick={() => onNavigate('coach')}>Voir le coach IA <span>→</span></button></section>
    </div>
    <section className="card weekly-card"><div className="section-heading"><div><p className="card-kicker">Les 7 derniers jours</p><h2>Votre rythme</h2></div>{weekly?.goal_adherence !== null && weekly?.goal_adherence !== undefined && <span className="subtle-pill">{Math.round(weekly.goal_adherence * 100)}% des jours dans la cible</span>}</div>{weekly ? <WeeklyChart weekly={weekly} /> : <p className="muted">Enregistrez des repas pour voir apparaître vos tendances.</p>}</section>
    <p className="medical-note">Les estimations et tendances sont fournies à titre informatif. Elles ne constituent pas un diagnostic et ne remplacent pas l’avis d’un professionnel de santé.</p>
  </div>
}

function NutrientBars({ daily }: { daily: DailySummary }) {
  const nutrients = [
    ['protein_g', 'Protéines', 'g', 'purple'], ['carbohydrates_g', 'Glucides', 'g', 'yellow'], ['fat_g', 'Lipides', 'g', 'coral'], ['fiber_g', 'Fibres', 'g', 'green'],
  ] as const
  return <div className="nutrient-list">{nutrients.map(([key, label, unit, color]) => { const value = daily.consumed[key]; const target = daily.targets[key]; const width = target ? Math.min(100, (value / target) * 100) : Math.min(100, value * 2); return <div className="nutrient-row" key={key}><div className="nutrient-label"><span className={`dot ${color}`} />{label}<strong>{formatNumber(value, 1)}{unit}</strong></div><div className="nutrient-track"><span className={color} style={{ width: `${width}%` }} /></div><small>{target ? `${formatNumber(target, 0)}${unit}` : '— cible'}</small></div> })}</div>
}

function WeeklyChart({ weekly }: { weekly: PeriodSummary }) {
  const max = Math.max(...weekly.days.map(day => day.consumed.calories), weekly.averages.calories, 1)
  return <div className="chart-wrap"><div className="bar-chart">{weekly.days.map(day => <div className="bar-column" key={day.date} title={`${formatNumber(day.consumed.calories)} kcal`}><div className="bar-value">{day.consumed.calories ? formatNumber(day.consumed.calories) : ''}</div><div className="bar" style={{ height: `${Math.max(day.consumed.calories ? 8 : 2, (day.consumed.calories / max) * 100)}%` }} /><span>{new Date(`${day.date}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'short' }).replace('.', '')}</span></div>)}</div><div className="chart-legend"><span><i className="legend-dot" /> Calories connues</span><span>Moyenne : {formatNumber(weekly.averages.calories)} kcal / jour</span></div></div>
}

function LogMeal({ onSaved }: { onSaved: () => Promise<void> }) {
  const [text, setText] = useState('')
  const [mealType, setMealType] = useState('lunch')
  const [parsed, setParsed] = useState<ParsedItem[]>([])
  const [clarification, setClarification] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const parse = async () => { if (!text.trim()) return; setBusy(true); setError(''); try { const result = await api.analyzeMeal(text); setParsed(result.items); setClarification(result.clarification) } catch (err) { setError(err instanceof Error ? err.message : 'Analyse indisponible.') } finally { setBusy(false) } }
  const save = async () => { if (!parsed.length || parsed.some(item => !item.quantity || !item.unit)) return; setBusy(true); setError(''); try { await api.addMeal({ meal_type: mealType, items: parsed.map(item => ({ food: item.food, quantity: item.quantity as number, unit: item.unit as string })) }); setMessage('Repas ajouté à votre journée.'); setText(''); setParsed([]); setClarification(null); await onSaved() } catch (err) { setError(err instanceof Error ? err.message : 'Enregistrement impossible.') } finally { setBusy(false) } }
  return <div className="page narrow-page"><div className="page-heading"><div><p className="eyebrow">Journal alimentaire</p><h1>Ajouter un repas</h1><p className="muted">Décrivez ce que vous avez mangé, naturellement.</p></div></div><section className="card meal-entry-card"><div className="ai-intro"><span className="large-sparkle">✧</span><div><strong>Assistant de saisie</strong><p>Exemple : « deux œufs, 150 g de riz et une pomme »</p></div></div><label>Type de repas<select value={mealType} onChange={e => setMealType(e.target.value)}><option value="breakfast">Petit-déjeuner</option><option value="lunch">Déjeuner</option><option value="dinner">Dîner</option><option value="snack">Collation</option><option value="drink">Boisson</option></select></label><label>Ce que j’ai mangé<textarea value={text} onChange={e => setText(e.target.value)} rows={5} placeholder="J'ai mangé…" /></label><button className="secondary-button" onClick={parse} disabled={busy || text.length < 3}>{busy ? 'Analyse…' : '✧ Structurer avec l’IA'}</button>{error && <p className="form-error">{error}</p>}{message && <p className="success-message">✓ {message}</p>}{parsed.length > 0 && <div className="parsed-result"><div className="section-heading"><div><p className="card-kicker">Vérifiez avant d’enregistrer</p><h3>Éléments détectés</h3></div><span className="subtle-pill">{parsed.length} élément{parsed.length > 1 ? 's' : ''}</span></div>{parsed.map((item, index) => <div className="parsed-item" key={`${item.food}-${index}`}><span className="food-icon">{index % 2 ? '◌' : '●'}</span><div><strong>{item.food}</strong>{item.needs_clarification ? <small className="warning-text">Quantité à préciser</small> : <small>{formatNumber(item.quantity, 1)} {item.unit}{item.estimated ? ' · estimé' : ''}</small>}</div>{item.needs_clarification && <input type="number" min="0.1" step="0.1" placeholder="qté" onChange={e => { const next = [...parsed]; next[index] = { ...item, quantity: Number(e.target.value) || null, unit: item.unit || 'portion', needs_clarification: !e.target.value }; setParsed(next) }} />}</div>)}{clarification && <p className="clarification">{clarification}</p>}<button className="primary-button full" onClick={save} disabled={busy || parsed.some(item => !item.quantity || !item.unit)}>Enregistrer ce repas</button><p className="muted tiny">Les valeurs nutritionnelles sans aliment correspondant au catalogue resteront explicitement inconnues.</p></div>}</section><p className="medical-note">L’IA aide à structurer votre texte, mais ne connaît pas automatiquement les recettes ni les quantités cachées. Vérifiez toujours la proposition.</p></div>
}

function History({ meals, weekly, onDelete }: { meals: Meal[]; weekly: PeriodSummary | null; onDelete: (id: string) => Promise<void> }) {
  const [deleting, setDeleting] = useState('')
  const grouped = useMemo(() => meals.reduce<Record<string, Meal[]>>((all, meal) => { const key = meal.eaten_at.slice(0, 10); (all[key] ||= []).push(meal); return all }, {}), [meals])
  return <div className="page"><div className="page-heading"><div><p className="eyebrow">Votre journal</p><h1>Historique</h1><p className="muted">Les repas que vous avez choisi de conserver.</p></div><div className="history-summary"><strong>{meals.length}</strong><span>repas affichés</span></div></div><div className="history-grid"><section className="card meal-history-card">{Object.keys(grouped).length === 0 && <EmptyState text="Aucun repas enregistré pour le moment." />}{Object.entries(grouped).map(([day, dayMeals]) => <div className="day-group" key={day}><div className="day-label"><span>{new Date(`${day}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}</span><i /></div>{dayMeals.map(meal => <div className="meal-line" key={meal.id}><span className={`meal-type-icon ${meal.meal_type}`}>{meal.meal_type === 'breakfast' ? '☼' : meal.meal_type === 'dinner' ? '◒' : '◌'}</span><div className="meal-info"><strong>{meal.items.map(item => item.food_name).join(', ')}</strong><span>{meal.meal_type} · {new Date(meal.eaten_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span></div><div className="meal-kcal">{meal.has_unknown_nutrition ? 'partiel' : `${formatNumber(meal.totals.calories)} kcal`}<button aria-label="Supprimer" className="delete-button" disabled={deleting === meal.id} onClick={async () => { setDeleting(meal.id); await onDelete(meal.id); setDeleting('') }}>×</button></div></div>)}</div>)}</section><section className="card side-summary"><p className="card-kicker">Sur 7 jours</p><h2>{weekly ? formatNumber(weekly.averages.calories) : '—'} <small>kcal / jour</small></h2><p className="muted">Une moyenne descriptive, calculée uniquement sur les aliments connus.</p>{weekly?.days.map(day => <div className="mini-day" key={day.date}><span>{new Date(`${day.date}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'short' })}</span><div><i style={{ width: `${Math.min(100, day.consumed.calories / Math.max(weekly.averages.calories, 1) * 100)}%` }} /></div><strong>{formatNumber(day.consumed.calories)}</strong></div>)}</section></div></div>
}

function Coach({ recommendations, onRefresh }: { recommendations: string[]; onRefresh: () => Promise<void> }) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [message, setMessage] = useState('')
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const ask = async () => { if (!message.trim()) return; setBusy(true); try { const result = await api.chat(message); setAnswer(result.answer); setMessage('') } finally { setBusy(false) } }
  const suggest = async () => { setBusy(true); try { const result = await api.suggestions('lunch'); setSuggestions(result.suggestions) } finally { setBusy(false) } }
  return <div className="page coach-page"><div className="page-heading"><div><p className="eyebrow">Espace de réflexion</p><h1>Votre coach IA <span className="sparkle">✧</span></h1><p className="muted">Des explications, pas des injonctions.</p></div><button className="secondary-button" onClick={() => void onRefresh()}>↻ Actualiser l’analyse</button></div><div className="coach-layout"><section className="card chat-card"><div className="chat-header"><div className="coach-avatar">✧</div><div><strong>Cal, votre assistant</strong><span>Contexte limité à votre espace</span></div><span className="online-dot" /></div><div className="chat-body"><div className="chat-bubble assistant">Bonjour ! Je peux commenter votre journée, vous aider à lire une tendance ou imaginer un repas compatible avec vos préférences.</div>{answer && <div className="chat-bubble assistant">{answer}</div>}</div><div className="quick-prompts"><button onClick={() => setMessage('Analyse ma journée')}>Analyse ma journée</button><button onClick={() => setMessage('Que pourrais-je manger ce soir ?')}>Une idée ce soir ?</button></div><div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} onKeyDown={e => e.key === 'Enter' && void ask()} placeholder="Posez votre question…" /><button onClick={ask} disabled={busy || !message.trim()}>↑</button></div><p className="tiny muted">Informations générales uniquement. Pour une situation médicale, consultez un professionnel.</p></section><section className="card coach-notes"><div className="section-heading"><div><p className="card-kicker">Aujourd’hui</p><h2>Observations</h2></div><span className="sparkle">✧</span></div>{recommendations.map((recommendation, index) => <div className="coach-note" key={recommendation}><span>{index + 1}</span><p>{recommendation}</p></div>)}<button className="outline-button full" onClick={suggest} disabled={busy}>Proposer un repas adapté</button></section></div>{suggestions.length > 0 && <section className="suggestion-grid">{suggestions.map(suggestion => <article className="card suggestion-card" key={suggestion.title}><div className="suggestion-art">◌</div><p className="card-kicker">Suggestion estimée</p><h2>{suggestion.title}</h2><ul>{suggestion.ingredients.map(ingredient => <li key={ingredient.food}>{ingredient.quantity} {ingredient.unit} · {ingredient.food}</li>)}</ul>{suggestion.notes.map(note => <p className="muted tiny" key={note}>{note}</p>)}</article>)}</section>}</div>
}

function ProfileEditor({ profile, onSaved }: { profile: Profile; onSaved: () => Promise<void> }) {
  const [form, setForm] = useState({ display_name: profile.display_name, age: profile.age?.toString() || '', sex: profile.sex || '', height_cm: profile.height_cm?.toString() || '', weight_kg: profile.weight_kg?.toString() || '', activity_level: profile.activity_level || '', goals: profile.goals.join(', '), dietary_preferences: profile.dietary_preferences.join(', '), allergies: profile.allergies.join(', '), intolerances: profile.intolerances.join(', '), favorite_foods: profile.favorite_foods.join(', '), avoid_foods: profile.avoid_foods.join(', '), meals_per_day: profile.meals_per_day?.toString() || '', country: profile.country || '', food_budget: profile.food_budget?.toString() || '', cultural_constraints: profile.cultural_constraints || '', daily_calorie_target: profile.daily_calorie_target?.toString() || '' })
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const update = (key: keyof typeof form, value: string) => setForm(current => ({ ...current, [key]: value }))
  const list = (value: string) => value.split(',').map(item => item.trim()).filter(Boolean)
  const save = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { await api.updateProfile({ display_name: form.display_name, age: form.age ? Number(form.age) : null, sex: form.sex || null, height_cm: form.height_cm ? Number(form.height_cm) : null, weight_kg: form.weight_kg ? Number(form.weight_kg) : null, activity_level: form.activity_level || null, goals: list(form.goals), dietary_preferences: list(form.dietary_preferences), allergies: list(form.allergies), intolerances: list(form.intolerances), favorite_foods: list(form.favorite_foods), avoid_foods: list(form.avoid_foods), meals_per_day: form.meals_per_day ? Number(form.meals_per_day) : null, country: form.country || null, food_budget: form.food_budget ? Number(form.food_budget) : null, cultural_constraints: form.cultural_constraints || null, daily_calorie_target: form.daily_calorie_target ? Number(form.daily_calorie_target) : null }); setMessage('Profil mis à jour.'); await onSaved() } catch (err) { setError(err instanceof Error ? err.message : 'Mise à jour impossible.') } finally { setBusy(false) } }
  return <div className="page narrow-page"><div className="page-heading"><div><p className="eyebrow">Votre contexte</p><h1>Mon profil</h1><p className="muted">Plus votre contexte est précis, plus les repères sont utiles.</p></div></div><form className="card profile-form" onSubmit={save}><div className="profile-section"><h2>Informations de base</h2><div className="form-grid"><label>Nom d’affichage<input value={form.display_name} onChange={e => update('display_name', e.target.value)} required /></label><label>Âge<input type="number" min="13" max="120" value={form.age} onChange={e => update('age', e.target.value)} placeholder="Optionnel" /></label><label>Sexe (optionnel)<select value={form.sex} onChange={e => update('sex', e.target.value)}><option value="">Non renseigné</option><option value="female">Femme</option><option value="male">Homme</option><option value="other">Autre</option><option value="prefer_not_to_say">Je préfère ne pas préciser</option></select></label><label>Taille (cm)<input type="number" min="80" max="250" value={form.height_cm} onChange={e => update('height_cm', e.target.value)} placeholder="Optionnel" /></label><label>Poids (kg)<input type="number" min="25" max="500" value={form.weight_kg} onChange={e => update('weight_kg', e.target.value)} placeholder="Optionnel" /></label><label>Activité<select value={form.activity_level} onChange={e => update('activity_level', e.target.value)}><option value="">Non renseignée</option><option value="sedentary">Sédentaire</option><option value="light">Légère</option><option value="moderate">Modérée</option><option value="very_active">Très active</option><option value="athlete">Sportive / athlète</option></select></label><label>Repas habituels / jour<input type="number" min="1" max="12" value={form.meals_per_day} onChange={e => update('meals_per_day', e.target.value)} placeholder="3" /></label></div></div><div className="profile-section"><h2>Préférences & objectifs</h2><div className="form-grid"><label className="wide">Objectifs <input value={form.goals} onChange={e => update('goals', e.target.value)} placeholder="équilibre, maintien du poids" /><small>Séparez les éléments par une virgule.</small></label><label className="wide">Préférences alimentaires <input value={form.dietary_preferences} onChange={e => update('dietary_preferences', e.target.value)} placeholder="végétarien, méditerranéen" /></label><label>Allergies <input value={form.allergies} onChange={e => update('allergies', e.target.value)} placeholder="arachide" /></label><label>Intolérances <input value={form.intolerances} onChange={e => update('intolerances', e.target.value)} placeholder="lactose" /></label><label>Aliments à éviter <input value={form.avoid_foods} onChange={e => update('avoid_foods', e.target.value)} placeholder="champignons" /></label><label>Aliments préférés <input value={form.favorite_foods} onChange={e => update('favorite_foods', e.target.value)} placeholder="lentilles, pommes" /></label><label>Pays / région <input value={form.country} onChange={e => update('country', e.target.value)} placeholder="France" /></label><label>Budget alimentaire <input type="number" min="0" value={form.food_budget} onChange={e => update('food_budget', e.target.value)} placeholder="Optionnel" /></label><label>Contraintes culturelles <input value={form.cultural_constraints} onChange={e => update('cultural_constraints', e.target.value)} placeholder="Optionnel" /></label><label>Repère calorique personnalisé <input type="number" min="800" max="10000" value={form.daily_calorie_target} onChange={e => update('daily_calorie_target', e.target.value)} placeholder="Laisser vide pour estimer" /><small>Sinon, CalTracker peut fournir une estimation transparente.</small></label></div></div>{error && <p className="form-error">{error}</p>}{message && <p className="success-message">✓ {message}</p>}<div className="form-actions"><span className="tiny muted">Ces champs restent privés à votre compte.</span><button className="primary-button" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer le profil'}</button></div></form></div>
}

function Privacy() { return <div className="page narrow-page"><div className="page-heading"><div><p className="eyebrow">Vos choix, vos données</p><h1>Confidentialité</h1><p className="muted">La transparence fait partie du produit.</p></div></div><section className="card privacy-card"><div className="privacy-hero"><span>⌁</span><div><h2>Un espace privé par conception</h2><p>Votre profil, vos repas et votre hydratation sont attachés à votre compte. Les requêtes sont toujours filtrées par votre identité.</p></div></div><div className="privacy-columns"><div><h3>Ce qui est collecté</h3><p>Votre adresse email, les informations de profil que vous choisissez de renseigner, vos repas saisis et votre hydratation optionnelle.</p></div><div><h3>Pourquoi</h3><p>Calculer des agrégats quotidiens, afficher vos tendances et personnaliser une demande que vous adressez au coach.</p></div><div><h3>IA et contexte</h3><p>Le fournisseur configuré reçoit uniquement le contexte nécessaire à la fonction demandée. Le mode local peut fonctionner sans clé API.</p></div><div><h3>Vos contrôles</h3><p>Vous pouvez exporter vos données ou supprimer votre compte. La suppression retire aussi les repas associés.</p></div></div><div className="privacy-callout"><strong>Important</strong><p>CalTracker propose des informations générales et des estimations. Ce n’est ni un diagnostic ni un traitement médical. Pour une allergie, une pathologie ou un objectif médical, demandez conseil à un professionnel.</p></div></section></div> }

function EmptyState({ text }: { text: string }) { return <div className="empty-state"><span>◌</span><p>{text}</p></div> }

export default App
