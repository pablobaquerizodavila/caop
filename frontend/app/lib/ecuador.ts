// Provincias del Ecuador con su ciudad capital y todas las cabeceras cantonales
// (221 cantones). En cada provincia, la capital va primero.
export interface EcProvince {
  province: string;
  capital: string;
  cities: string[];
}

export const EC_PROVINCES: EcProvince[] = [
  {
    province: "Azuay",
    capital: "Cuenca",
    cities: [
      "Cuenca", "Girón", "Gualaceo", "Nabón", "Paute", "Pucará", "San Fernando",
      "Santa Isabel", "Sígsig", "Oña", "Chordeleg", "El Pan", "Sevilla de Oro",
      "Guachapala", "Camilo Ponce Enríquez",
    ],
  },
  {
    province: "Bolívar",
    capital: "Guaranda",
    cities: ["Guaranda", "Chillanes", "San José de Chimbo", "Echeandía", "San Miguel", "Caluma", "Las Naves"],
  },
  {
    province: "Cañar",
    capital: "Azogues",
    cities: ["Azogues", "Biblián", "Cañar", "La Troncal", "El Tambo", "Déleg", "Suscal"],
  },
  {
    province: "Carchi",
    capital: "Tulcán",
    cities: ["Tulcán", "Bolívar", "El Ángel", "Mira", "San Gabriel", "Huaca"],
  },
  {
    province: "Chimborazo",
    capital: "Riobamba",
    cities: [
      "Riobamba", "Alausí", "Villa La Unión (Cajabamba)", "Chambo", "Chunchi",
      "Guamote", "Guano", "Pallatanga", "Penipe", "Cumandá",
    ],
  },
  {
    province: "Cotopaxi",
    capital: "Latacunga",
    cities: ["Latacunga", "La Maná", "El Corazón", "Pujilí", "San Miguel de Salcedo", "Saquisilí", "Sigchos"],
  },
  {
    province: "El Oro",
    capital: "Machala",
    cities: [
      "Machala", "Arenillas", "Paccha", "Balsas", "Chilla", "El Guabo", "Huaquillas",
      "Marcabelí", "Pasaje", "Piñas", "Portovelo", "Santa Rosa", "Zaruma", "La Victoria",
    ],
  },
  {
    province: "Esmeraldas",
    capital: "Esmeraldas",
    cities: ["Esmeraldas", "Valdez (Limones)", "Muisne", "Rosa Zárate", "San Lorenzo", "Atacames", "Rioverde"],
  },
  {
    province: "Galápagos",
    capital: "Puerto Baquerizo Moreno",
    cities: ["Puerto Baquerizo Moreno", "Puerto Villamil", "Puerto Ayora"],
  },
  {
    province: "Guayas",
    capital: "Guayaquil",
    cities: [
      "Guayaquil", "Jujan", "Balao", "Balzar", "Colimes", "Daule", "Durán",
      "Velasco Ibarra (El Empalme)", "El Triunfo", "Milagro", "Naranjal", "Naranjito",
      "Palestina", "Pedro Carbo", "Samborondón", "Santa Lucía", "Salitre", "Yaguachi",
      "Playas", "Simón Bolívar", "Coronel Marcelino Maridueña", "Lomas de Sargentillo",
      "Nobol", "Bucay", "Isidro Ayora",
    ],
  },
  {
    province: "Imbabura",
    capital: "Ibarra",
    cities: ["Ibarra", "Atuntaqui", "Cotacachi", "Otavalo", "Pimampiro", "Urcuquí"],
  },
  {
    province: "Loja",
    capital: "Loja",
    cities: [
      "Loja", "Cariamanga", "Catamayo", "Celica", "Chaguarpamba", "Amaluza", "Gonzanamá",
      "Macará", "Catacocha", "Alamor", "Saraguro", "Sozoranga", "Zapotillo", "Pindal",
      "Quilanga", "Olmedo",
    ],
  },
  {
    province: "Los Ríos",
    capital: "Babahoyo",
    cities: [
      "Babahoyo", "Baba", "Montalvo", "Puebloviejo", "Quevedo", "Catarama", "Ventanas",
      "Vinces", "Palenque", "San Jacinto de Buena Fe", "Valencia", "Mocache", "Quinsaloma",
    ],
  },
  {
    province: "Manabí",
    capital: "Portoviejo",
    cities: [
      "Portoviejo", "Calceta", "Chone", "El Carmen", "Flavio Alfaro", "Jipijapa", "Junín",
      "Manta", "Montecristi", "Paján", "Pichincha", "Rocafuerte", "Santa Ana",
      "Bahía de Caráquez", "Tosagua", "Sucre", "Pedernales", "Olmedo", "Puerto López",
      "Jama", "Jaramijó", "San Vicente",
    ],
  },
  {
    province: "Morona Santiago",
    capital: "Macas",
    cities: [
      "Macas", "Gualaquiza", "General Leonidas Plaza Gutiérrez (Limón)", "Palora",
      "Santiago de Méndez", "Sucúa", "Huamboya", "San Juan Bosco", "Taisha", "Logroño",
      "Pablo Sexto", "Santiago (Tiwintza)",
    ],
  },
  {
    province: "Napo",
    capital: "Tena",
    cities: ["Tena", "Archidona", "El Chaco", "Baeza", "Carlos Julio Arosemena Tola"],
  },
  {
    province: "Orellana",
    capital: "Puerto Francisco de Orellana",
    cities: ["Puerto Francisco de Orellana", "Nuevo Rocafuerte", "La Joya de los Sachas", "Loreto"],
  },
  {
    province: "Pastaza",
    capital: "Puyo",
    cities: ["Puyo", "Mera", "Santa Clara", "Arajuno"],
  },
  {
    province: "Pichincha",
    capital: "Quito",
    cities: [
      "Quito", "Cayambe", "Machachi", "Tabacundo", "Sangolquí",
      "San Miguel de los Bancos", "Pedro Vicente Maldonado", "Puerto Quito",
    ],
  },
  {
    province: "Santa Elena",
    capital: "Santa Elena",
    cities: ["Santa Elena", "La Libertad", "Salinas"],
  },
  {
    province: "Santo Domingo de los Tsáchilas",
    capital: "Santo Domingo",
    cities: ["Santo Domingo", "La Concordia"],
  },
  {
    province: "Sucumbíos",
    capital: "Nueva Loja",
    cities: [
      "Nueva Loja", "El Dorado de Cascales", "Tarapoa", "Lumbaquí",
      "Puerto El Carmen de Putumayo", "Shushufindi", "La Bonita",
    ],
  },
  {
    province: "Tungurahua",
    capital: "Ambato",
    cities: ["Ambato", "Baños de Agua Santa", "Cevallos", "Mocha", "Patate", "Quero", "Pelileo", "Píllaro", "Tisaleo"],
  },
  {
    province: "Zamora Chinchipe",
    capital: "Zamora",
    cities: [
      "Zamora", "Zumba", "Guayzimi", "28 de Mayo", "Yantzaza", "El Pangui",
      "Zumbi", "Palanda", "Paquisha",
    ],
  },
];

/** Capital de una provincia (o "" si no se encuentra). */
export function capitalOf(province: string): string {
  return EC_PROVINCES.find((p) => p.province === province)?.capital ?? "";
}

/** Cabeceras cantonales de una provincia (vacío si no se encuentra). */
export function citiesOf(province: string): string[] {
  return EC_PROVINCES.find((p) => p.province === province)?.cities ?? [];
}
