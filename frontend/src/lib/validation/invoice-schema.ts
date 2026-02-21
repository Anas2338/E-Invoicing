import { z } from 'zod';

// Common address schema
const addressSchema = z.object({
  street: z.string().min(1, 'Street is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().min(1, 'State is required'),
  zipCode: z.string().min(1, 'ZIP code is required'),
  country: z.string().min(1, 'Country is required'),
});

// Contact info schema
const contactInfoSchema = z.object({
  phone: z.string().optional(),
  email: z.string().email('Invalid email format').optional(),
}).optional();

// Customer/Supplier info schema
const partyInfoSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  taxId: z.string().min(1, 'Tax ID is required'),
  address: addressSchema,
  contact: contactInfoSchema,
});

// Line item schema
const lineItemSchema = z.object({
  id: z.string().optional(),
  description: z.string().min(1, 'Description is required'),
  quantity: z.number().positive('Quantity must be positive'),
  unitPrice: z.number().positive('Unit price must be positive'),
  taxRate: z.number().min(0).max(1).optional(),
});

// Invoice schema
export const invoiceSchema = z.object({
  type: z.enum(['sale', 'purchase']).describe('Invoice type is required'),
  invoiceNumber: z.string().min(1, 'Invoice number is required'),
  date: z.string().refine(date => !isNaN(Date.parse(date)), {
    message: 'Date is required and must be valid'
  }),
  dueDate: z.string().refine(date => !isNaN(Date.parse(date)), {
    message: 'Due date is required and must be valid'
  }),
  customerInfo: partyInfoSchema.optional(),
  supplierInfo: partyInfoSchema.optional(),
  lineItems: z.array(lineItemSchema).min(1, 'At least one line item is required'),
  environment: z.enum(['sandbox', 'production']),
  saveAsDraft: z.boolean().default(true),
});

// Validate that customerInfo is required for sale invoices and supplierInfo for purchase invoices
export const validatedInvoiceSchema = invoiceSchema.refine(
  (data) => {
    if (data.type === 'sale') {
      return data.customerInfo !== undefined;
    }
    if (data.type === 'purchase') {
      return data.supplierInfo !== undefined;
    }
    return true;
  },
  {
    message: 'Customer information is required for sale invoices',
    path: ['customerInfo'],
  }
).refine(
  (data) => {
    if (data.type === 'purchase') {
      return data.supplierInfo !== undefined;
    }
    if (data.type === 'sale') {
      return data.supplierInfo !== undefined;
    }
    return true;
  },
  {
    message: 'Supplier information is required for purchase invoices',
    path: ['supplierInfo'],
  }
);

// Export the types
export type InvoiceFormData = z.infer<typeof validatedInvoiceSchema>;
export type LineItemData = z.infer<typeof lineItemSchema>;
export type PartyInfoData = z.infer<typeof partyInfoSchema>;