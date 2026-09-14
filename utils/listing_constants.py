# Mirrors the frontend constant lists (apps/dashboard/src/data/regions.ts and
# apps/dashboard/src/pages/admin/SubmitListing.tsx). Region/features/tags are
# free-text columns in the DB, so these are used only to *warn* on import rows
# with unrecognized values, never to block them.

POPULAR_AREAS = [
    "Cap Cana", "Cabarete", "Jarabacoa", "Las Terrenas", "Punta Cana",
    "Puerto Plata", "Samaná", "Santo Domingo", "Santiago", "Sosúa",
]

DR_PROVINCES = [
    "Azua", "Bahoruco", "Barahona", "Dajabón", "Distrito Nacional", "Duarte",
    "El Seibo", "Elías Piña", "Espaillat", "Hato Mayor", "Hermanas Mirabal",
    "Independencia", "La Altagracia", "La Romana", "La Vega",
    "María Trinidad Sánchez", "Monseñor Nouel", "Monte Cristi", "Monte Plata",
    "Pedernales", "Peravia", "Puerto Plata", "Samaná", "San Cristóbal",
    "San José de Ocoa", "San Juan", "San Pedro de Macorís", "Sánchez Ramírez",
    "Santiago", "Santiago Rodríguez", "Santo Domingo", "Valverde",
]

ALL_REGIONS = set(POPULAR_AREAS) | set(DR_PROVINCES)

FEATURES = {
    "Pool", "Ocean View", "Beachfront", "Oceanfront", "Furnished", "Beach Access",
    "Mountain View", "Parking", "Gym", "Smart Home", "Backup Generator", "Solar Panels",
}

BASE_TAGS = {
    "Luxury", "New", "Investment", "Commercial", "Pet Friendly", "Short Term",
    "Long Term", "Furnished", "Ocean View", "Mountain View",
}
