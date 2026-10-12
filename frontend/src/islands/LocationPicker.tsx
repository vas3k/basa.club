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

    const cities = countries.find((c) => c.id === countryId)?.cities ?? [];
    const wholeWorld = allowEverywhere && countryId === everywhere;

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
                        setCountryId(event.target.value);
                        setCityId(allowEverywhere ? everywhere : "");
                    }}
                >
                    {allowEverywhere ? (
                        <option value={everywhere}>🌎 Весь мир</option>
                    ) : (
                        <option value="" disabled>
                            Выберите страну
                        </option>
                    )}
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
                    {wholeWorld && <input type="hidden" name="city" value={everywhere} />}
                    <select
                        id="id_city"
                        name={wholeWorld ? undefined : "city"}
                        value={wholeWorld ? everywhere : cityId}
                        disabled={wholeWorld}
                        onChange={(event) => setCityId(event.target.value)}
                    >
                        {allowEverywhere ? (
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
