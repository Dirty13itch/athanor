export type PropertyType = "single_family" | "townhome" | "duplex" | "multifamily" | "commercial";

export interface Address {
  street: string;
  city: string;
  state: string;
  zip: string;
}

export interface Client {
  id: string;
  name: string;
  company?: string;
  email: string;
  phone?: string;
  address?: Address;
  createdAt: string;
}

export interface Project {
  id: string;
  name: string;
  clientId: string;
  client?: Client;
  address: Address;
  propertyType: PropertyType;
  builderName: string;
  status: "active" | "completed" | "archived";
  inspectionCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProjectRequest {
  name: string;
  clientId?: string;
  clientName?: string;
  clientEmail?: string;
  address: Address;
  propertyType: PropertyType;
  builderName: string;
}
