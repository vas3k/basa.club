import { useState } from "react";

import type { CountryOption } from "../types";

type Props = {
    countries: CountryOption[];
    country?: string;
    city?: string;
    onlineCountryId: string;
};

export default function LocationPicker({ countries, country = "", city = "", onlineCountryId }: Props) {
    const [countryId, setCountryId] = useState(country);
    const [cityId, setCityId] = useState(city);
    const cities = countries.find((c) => c.id === countryId)?.cities ?? [];
    const online = countries.find((c) => c.id === onlineCountryId);

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
                    <option value="" disabled>Выберите страну</option>
                    {online && <option value={online.id}>{online.icon} {online.name}</option>}
                    {online && <option disabled value="separator">─────────</option>}
                    {countries.filter((c) => c.id !== onlineCountryId).map((c) => (
                        <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                    ))}
                </select>
            </div>

            {cities.length > 0 ? (
                <div className="form-group">
                    <label htmlFor="id_city">Город</label>
                    <select id="id_city" name="city" value={cityId} onChange={(event) => setCityId(event.target.value)}>
                        <option value="">Вся страна</option>
                        {cities.map((c) => (
                            <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                        ))}
                    </select>
                </div>
            ) : <input type="hidden" name="city" value="" />}
        </div>
    );
}
