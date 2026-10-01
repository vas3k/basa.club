export type Option = {
    id: string;
    name: string;
    icon?: string;
};

export type CountryOption = Option & {
    cities: Option[];
};

export type CategoryOption = Option & {
    children: Option[];
};
