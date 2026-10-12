import { useState } from "react";

import type { CountryOption } from "../types";

type Props = {
    countries: CountryOption[];
    country?: string;
    city?: string;
    allowEverywhere?: boolean;
};

const everywhere = "everywhere";

export default function LocationPicker({ countries, country = "", city = "", allowEverywhere = false }: Props) {
    const [countryId, setCountryId] = useState(country);
    const [cityId, setCityId] = useState(city || (allowEverywhere ? everywhere : ""));

    const wholeWorld = countryId === everywhere;
    const cities = countries.find((c) => c.id === countryId)?.cities ?? [];

    return (
        <div className="form-row">
            <div className="form-group">
                <label htmlFor="id_country">Страна</label>
                <select
                    id="id_country"
                    name="country"
                    required
                    value={countryId}
                    onChange={(event) => {
                        const nextCountry = event.target.value;
                        setCountryId(nextCountry);
                        setCityId(nextCountry === everywhere || allowEverywhere ? everywhere : "");
                    }}
                >
                    <option value="" disabled>
                        Выберите страну
                    </option>
                    <option value={everywhere}>🌎 Весь мир</option>
                    {countries.map((c) => (
                        <option key={c.id} value={c.id}>
                            {c.icon} {c.name}
                        </option>
                    ))}
                </select>
            </div>

            {countryId && (
                <div className="form-group">
                    <label htmlFor="id_city">Город</label>
                    {wholeWorld && <input type="hidden" name="city" value="" />}
                    <select
                        id="id_city"
                        name={wholeWorld ? undefined : "city"}
                        value={wholeWorld ? everywhere : cityId}
                        disabled={wholeWorld}
                        onChange={(event) => setCityId(event.target.value)}
                    >
                        {wholeWorld || allowEverywhere ? (
                            <option value={everywhere}>Везде</option>
                        ) : (
                            <option value="">Вся страна</option>
                        )}
                        {cities.map((c) => (
                            <option key={c.id} value={c.id}>
                                {c.icon} {c.name}
                            </option>
                        ))}
                    </select>
                </div>
            )}
        </div>
    );
}
