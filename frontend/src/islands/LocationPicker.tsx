import { useState } from "react";

import type { CountryOption } from "../types";

type Props = {
    countries: CountryOption[];
    country?: string;
    city?: string;
};

export default function LocationPicker({ countries, country = "", city = "" }: Props) {
    const [countryId, setCountryId] = useState(country);
    const [cityId, setCityId] = useState(city);

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
                        setCountryId(event.target.value);
                        setCityId("");
                    }}
                >
                    <option value="" disabled>
                        Выберите страну
                    </option>
                    {countries.map((c) => (
                        <option key={c.id} value={c.id}>
                            {c.icon} {c.name}
                        </option>
                    ))}
                </select>
            </div>

            <div className="form-group">
                <label htmlFor="id_city">Город</label>
                <select
                    id="id_city"
                    name="city"
                    value={cityId}
                    disabled={!countryId}
                    onChange={(event) => setCityId(event.target.value)}
                >
                    <option value="">Вся страна</option>
                    {cities.map((c) => (
                        <option key={c.id} value={c.id}>
                            {c.icon} {c.name}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
}
