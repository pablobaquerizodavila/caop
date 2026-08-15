// Provincias del Ecuador y su ciudad capital (24 provincias).
export const EC_PROVINCES: { province: string; capital: string }[] = [
  { province: "Azuay", capital: "Cuenca" },
  { province: "Bolívar", capital: "Guaranda" },
  { province: "Cañar", capital: "Azogues" },
  { province: "Carchi", capital: "Tulcán" },
  { province: "Chimborazo", capital: "Riobamba" },
  { province: "Cotopaxi", capital: "Latacunga" },
  { province: "El Oro", capital: "Machala" },
  { province: "Esmeraldas", capital: "Esmeraldas" },
  { province: "Galápagos", capital: "Puerto Baquerizo Moreno" },
  { province: "Guayas", capital: "Guayaquil" },
  { province: "Imbabura", capital: "Ibarra" },
  { province: "Loja", capital: "Loja" },
  { province: "Los Ríos", capital: "Babahoyo" },
  { province: "Manabí", capital: "Portoviejo" },
  { province: "Morona Santiago", capital: "Macas" },
  { province: "Napo", capital: "Tena" },
  { province: "Orellana", capital: "Puerto Francisco de Orellana" },
  { province: "Pastaza", capital: "Puyo" },
  { province: "Pichincha", capital: "Quito" },
  { province: "Santa Elena", capital: "Santa Elena" },
  { province: "Santo Domingo de los Tsáchilas", capital: "Santo Domingo" },
  { province: "Sucumbíos", capital: "Nueva Loja" },
  { province: "Tungurahua", capital: "Ambato" },
  { province: "Zamora Chinchipe", capital: "Zamora" },
];

/** Capital de una provincia (o "" si no se encuentra). */
export function capitalOf(province: string): string {
  return EC_PROVINCES.find((p) => p.province === province)?.capital ?? "";
}
